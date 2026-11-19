import torch

try:
    import triton
    import triton.language as tl
    HAS_TRITON = True
except Exception:
    HAS_TRITON = False

STATE = {"triton": HAS_TRITON}
ACT = {"dtype": torch.bfloat16}


# ----------------------------------------------------------------- torch references
def _rms_ref(x, w, eps, out_dtype):
    xf = x.float()
    return (xf * torch.rsqrt(xf.pow(2).mean(-1, keepdim=True) + eps) * w).to(out_dtype)


def _swiglu_ref(gu):
    g, u = gu.chunk(2, dim=-1)
    return torch.nn.functional.silu(g) * u


def _ce_ref(logits, targets, z):
    lf = logits.float()
    lse = torch.logsumexp(lf, dim=-1)
    tgt = lf.gather(-1, targets[:, None]).squeeze(-1)
    nll = lse - tgt
    return nll + z * lse.pow(2), nll.detach()


if HAS_TRITON:
    @triton.jit
    def _rms_fwd(x_ptr, w_ptr, y_ptr, rstd_ptr, D, eps, BLOCK: tl.constexpr):
        row = tl.program_id(0).to(tl.int64)
        cols = tl.arange(0, BLOCK)
        m = cols < D
        x = tl.load(x_ptr + row * D + cols, mask=m, other=0.0).to(tl.float32)
        var = tl.sum(x * x, axis=0) / D
        rstd = 1.0 / tl.sqrt(var + eps)
        w = tl.load(w_ptr + cols, mask=m, other=0.0).to(tl.float32)
        y = x * rstd * w
        tl.store(y_ptr + row * D + cols, y.to(y_ptr.dtype.element_ty), mask=m)
        tl.store(rstd_ptr + row, rstd)

    @triton.jit
    def _rms_bwd(x_ptr, w_ptr, dy_ptr, rstd_ptr, dx_ptr, dwp_ptr, n_rows, D,
                 BLOCK: tl.constexpr, NPROG: tl.constexpr):
        pid = tl.program_id(0)
        cols = tl.arange(0, BLOCK)
        m = cols < D
        w = tl.load(w_ptr + cols, mask=m, other=0.0).to(tl.float32)
        dw = tl.zeros([BLOCK], tl.float32)
        for row in range(pid, n_rows, NPROG):
            r = row.to(tl.int64)
            x = tl.load(x_ptr + r * D + cols, mask=m, other=0.0).to(tl.float32)
            dy = tl.load(dy_ptr + r * D + cols, mask=m, other=0.0).to(tl.float32)
            rstd = tl.load(rstd_ptr + r)
            xh = x * rstd
            wdy = dy * w
            c = tl.sum(xh * wdy, axis=0) / D
            dx = (wdy - xh * c) * rstd
            tl.store(dx_ptr + r * D + cols, dx.to(dx_ptr.dtype.element_ty), mask=m)
            dw += dy * xh
        tl.store(dwp_ptr + pid * D + cols, dw, mask=m)

    @triton.jit
    def _swiglu_fwd(gu_ptr, out_ptr, H, BLOCK: tl.constexpr):
        row = tl.program_id(0).to(tl.int64)
        cols = tl.program_id(1) * BLOCK + tl.arange(0, BLOCK)
        m = cols < H
        g = tl.load(gu_ptr + row * 2 * H + cols, mask=m, other=0.0).to(tl.float32)
        u = tl.load(gu_ptr + row * 2 * H + H + cols, mask=m, other=0.0).to(tl.float32)
        y = g * tl.sigmoid(g) * u
        tl.store(out_ptr + row * H + cols, y.to(out_ptr.dtype.element_ty), mask=m)

    @triton.jit
    def _swiglu_bwd(gu_ptr, dy_ptr, dgu_ptr, H, BLOCK: tl.constexpr):
        row = tl.program_id(0).to(tl.int64)
        cols = tl.program_id(1) * BLOCK + tl.arange(0, BLOCK)
        m = cols < H
        g = tl.load(gu_ptr + row * 2 * H + cols, mask=m, other=0.0).to(tl.float32)
        u = tl.load(gu_ptr + row * 2 * H + H + cols, mask=m, other=0.0).to(tl.float32)
        dy = tl.load(dy_ptr + row * H + cols, mask=m, other=0.0).to(tl.float32)
        s = tl.sigmoid(g)
        dg = dy * u * s * (1.0 + g * (1.0 - s))
        du = dy * g * s
        tl.store(dgu_ptr + row * 2 * H + cols, dg.to(dgu_ptr.dtype.element_ty), mask=m)
        tl.store(dgu_ptr + row * 2 * H + H + cols, du.to(dgu_ptr.dtype.element_ty), mask=m)

    @triton.jit
    def _ce_fwd(lg_ptr, tgt_ptr, row_ptr, nll_ptr, lse_ptr, V, z, BLOCK: tl.constexpr):
        row = tl.program_id(0).to(tl.int64)
        base = lg_ptr + row * V
        offs = tl.arange(0, BLOCK)
        mx = tl.full([BLOCK], -1e30, tl.float32)
        for s in range(0, V, BLOCK):
            cols = s + offs
            x = tl.load(base + cols, mask=cols < V, other=-1e30).to(tl.float32)
            mx = tl.maximum(mx, x)
        mval = tl.max(mx, axis=0)
        acc = tl.zeros([BLOCK], tl.float32)
        for s in range(0, V, BLOCK):
            cols = s + offs
            x = tl.load(base + cols, mask=cols < V, other=-1e30).to(tl.float32)
            acc += tl.exp(x - mval)
        lse = mval + tl.log(tl.sum(acc, axis=0))
        t = tl.load(tgt_ptr + row)
        tgt_logit = tl.load(base + t).to(tl.float32)
        nll = lse - tgt_logit
        tl.store(nll_ptr + row, nll)
        tl.store(lse_ptr + row, lse)
        tl.store(row_ptr + row, nll + z * lse * lse)

    @triton.jit
    def _ce_bwd(lg_ptr, tgt_ptr, lse_ptr, g_ptr, dl_ptr, V, z, BLOCK: tl.constexpr):
        row = tl.program_id(0).to(tl.int64)
        cols = tl.program_id(1) * BLOCK + tl.arange(0, BLOCK)
        m = cols < V
        x = tl.load(lg_ptr + row * V + cols, mask=m, other=-1e30).to(tl.float32)
        lse = tl.load(lse_ptr + row)
        g = tl.load(g_ptr + row)
        t = tl.load(tgt_ptr + row)
        p = tl.exp(x - lse)
        d = g * ((1.0 + 2.0 * z * lse) * p - tl.where(cols == t, 1.0, 0.0))
        tl.store(dl_ptr + row * V + cols, d.to(dl_ptr.dtype.element_ty), mask=m)

    class _RMS(torch.autograd.Function):
        @staticmethod
        def forward(ctx, x, w, eps, out_dtype):
            shape = x.shape
            D = shape[-1]
            x2 = x.reshape(-1, D).contiguous()
            n = x2.shape[0]
            y = torch.empty((n, D), dtype=out_dtype, device=x.device)
            rstd = torch.empty(n, dtype=torch.float32, device=x.device)
            _rms_fwd[(n,)](x2, w, y, rstd, D, eps, BLOCK=triton.next_power_of_2(D))
            ctx.save_for_backward(x2, w, rstd)
            ctx.shape = shape
            return y.view(shape)

        @staticmethod
        def backward(ctx, dy):
            x2, w, rstd = ctx.saved_tensors
            n, D = x2.shape
            dy2 = dy.reshape(-1, D).contiguous()
            dx = torch.empty_like(x2)
            nprog = min(256, n)
            dwp = torch.empty((nprog, D), dtype=torch.float32, device=x2.device)
            _rms_bwd[(nprog,)](x2, w, dy2, rstd, dx, dwp, n, D,
                               BLOCK=triton.next_power_of_2(D), NPROG=nprog)
            return dx.view(ctx.shape), dwp.sum(0).to(w.dtype), None, None

    class _SwiGLU(torch.autograd.Function):
        @staticmethod
        def forward(ctx, gu):
            shp = gu.shape
            H = shp[-1] // 2
            g2 = gu.reshape(-1, 2 * H).contiguous()
            n = g2.shape[0]
            out = torch.empty((n, H), dtype=gu.dtype, device=gu.device)
            _swiglu_fwd[(n, triton.cdiv(H, 512))](g2, out, H, BLOCK=512)
            ctx.save_for_backward(g2)
            return out.view(*shp[:-1], H)

        @staticmethod
        def backward(ctx, dy):
            (g2,) = ctx.saved_tensors
            n, H2 = g2.shape
            H = H2 // 2
            dy2 = dy.reshape(-1, H).contiguous()
            dgu = torch.empty_like(g2)
            _swiglu_bwd[(n, triton.cdiv(H, 512))](g2, dy2, dgu, H, BLOCK=512)
            return dgu.view(*dy.shape[:-1], H2)

    class _CE(torch.autograd.Function):
        @staticmethod
        def forward(ctx, logits, targets, z):
            N, V = logits.shape
            row = torch.empty(N, dtype=torch.float32, device=logits.device)
            nll = torch.empty_like(row)
            lse = torch.empty_like(row)
            _ce_fwd[(N,)](logits, targets, row, nll, lse, V, z, BLOCK=4096)
            ctx.save_for_backward(logits, targets, lse)
            ctx.z = z
            ctx.mark_non_differentiable(nll)
            return row, nll

        @staticmethod
        def backward(ctx, g_row, g_nll):
            logits, targets, lse = ctx.saved_tensors
            N, V = logits.shape
            dl = torch.empty_like(logits)
            _ce_bwd[(N, triton.cdiv(V, 4096))](logits, targets, lse, g_row.contiguous(), dl, V, ctx.z, BLOCK=4096)
            return dl, None, None


# ----------------------------------------------------------------- public API
def rms_norm(x, w, eps, out_dtype):
    if STATE["triton"] and x.is_cuda:
        return _RMS.apply(x, w, eps, out_dtype)
    return _rms_ref(x, w, eps, out_dtype)


def swiglu(gu):
    if STATE["triton"] and gu.is_cuda:
        return _SwiGLU.apply(gu)
    return _swiglu_ref(gu)


def fused_ce(logits, targets, z):
    """logits (N,V), targets (N,) -> (per-row loss incl. z-loss, per-row nll [no grad])"""
    if STATE["triton"] and logits.is_cuda:
        return _CE.apply(logits.contiguous(), targets.contiguous(), float(z))
    return _ce_ref(logits, targets, z)


def _close(a, b, tol=0.06):
    a, b = a.float(), b.float()
    return bool((a - b).abs().max() <= tol * b.abs().max() + 1e-5)


def selftest(device="cuda"):
    """Compares every Triton kernel (fwd+bwd) with its PyTorch reference. Returns (ok, message)."""
    if not HAS_TRITON:
        return False, "triton not installed"
    try:
        torch.manual_seed(0)
        for rows, D in ((37, 512), (300, 64)):
            x = torch.randn(rows, D, device=device, requires_grad=True)
            w = torch.randn(D, device=device, requires_grad=True)
            gy = torch.randn(rows, D, device=device).bfloat16()
            y = _RMS.apply(x, w, 1e-6, torch.bfloat16)
            y.backward(gy)
            dx, dw = x.grad.clone(), w.grad.clone()
            x.grad = None
            w.grad = None
            y2 = _rms_ref(x, w, 1e-6, torch.bfloat16)
            y2.backward(gy)
            if not (_close(y, y2) and _close(dx, x.grad) and _close(dw, w.grad)):
                return False, f"rmsnorm mismatch (D={D})"
        gu = torch.randn(11, 100 * 2, device=device).bfloat16().requires_grad_()
        gy = torch.randn(11, 100, device=device).bfloat16()
        y = _SwiGLU.apply(gu)
        y.backward(gy)
        d1 = gu.grad.clone()
        gu.grad = None
        y2 = _swiglu_ref(gu)
        y2.backward(gy)
        if not (_close(y, y2) and _close(d1, gu.grad)):
            return False, "swiglu mismatch"
        lg = (torch.randn(48, 5000, device=device) * 3).bfloat16().requires_grad_()
        tg = torch.randint(0, 5000, (48,), device=device)
        wt = torch.rand(48, device=device) + 0.5
        row, nll = _CE.apply(lg, tg, 1e-4)
        (row * wt).sum().backward()
        d1 = lg.grad.clone()
        lf = lg.detach().float().requires_grad_()
        row2, nll2 = _ce_ref(lf, tg, 1e-4)
        (row2 * wt).sum().backward()
        if not (_close(row, row2) and _close(nll, nll2) and _close(d1, lf.grad, 0.05)):
            return False, "fused cross-entropy mismatch"
        torch.cuda.synchronize()
        return True, "rmsnorm + swiglu + fused cross-entropy"
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:150]}"
