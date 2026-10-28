#!/usr/bin/env python3
"""Profundidad estéreo a partir de pares IR izquierda/derecha del CR-Scan Otter (capturados con otter_bridge.py).

Uso: profundidad.py DIR_CAPTURA DIR_SALIDA
  DIR_CAPTURA contiene ir_l_<ts>.pgm e ir_r_<ts>.pgm; se promedian hasta 8 pares con el mismo timestamp.
  Salida: depth_view.png (IR + profundidad), cloud.ply (puntos en mm) y Z.npy.

Parámetros de calibración leídos del escáner (getStructData 4037): f = 1581.52 px, cx izquierda 954.55,
cx derecha 314.55 (diferencia 640 px), cy 394.76. La línea base B = 50.072 mm viene de la estructura 0xFBA
(getRawData, 28 bytes: +0x4 baseline, +0xc focalPix 1581.52, +0x10 unit 1.0, +0x14 dispOffset 640).
"""
import glob, os, sys, numpy as np, cv2
F, CX_L, CX_R, CY, B = 1581.52, 954.55, 314.55, 394.76, 50.072
DOFFS = CX_L - CX_R
def load_pair(d, n=None):
    ts = sorted(set(os.path.basename(f)[5:] for f in glob.glob(f'{d}/ir_l_*')) & set(os.path.basename(f)[5:] for f in glob.glob(f'{d}/ir_r_*')))
    ts = ts[:n] if n else ts
    L = np.mean([cv2.imread(f'{d}/ir_l_{t}', cv2.IMREAD_UNCHANGED) for t in ts], axis=0)
    R = np.mean([cv2.imread(f'{d}/ir_r_{t}', cv2.IMREAD_UNCHANGED) for t in ts], axis=0)
    return L, R, len(ts)
def depth(L, R, zmin=200.0, zmax=1500.0):
    """Z en mm para cada píxel de la imagen izquierda (0 = sin dato)."""
    n = lambda a: cv2.normalize(a, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    H, W = L.shape
    dmin = int(np.floor(F * B / zmax)); dmax = int(np.ceil(F * B / zmin))
    nd = ((dmax - dmin) // 16 + 1) * 16
    # x_R' = x_R + DOFFS  =>  xL - xR' = d_true (< 0). Lienzo de ancho W + DOFFS para no perder columnas de R.
    S = int(round(DOFFS)); WW = W + S
    Lc = np.zeros((H, WW), np.uint8); Lc[:, :W] = n(L)
    Rc = np.zeros((H, WW), np.uint8); Rc[:, S:] = n(R)
    # Espejo horizontal => disparidad positiva |d_true|; relleno a la izquierda para que SGBM no recorte.
    Lf, Rf = Lc[:, ::-1], Rc[:, ::-1]
    pad = dmin + nd
    Lp = cv2.copyMakeBorder(Lf, 0, 0, pad, 0, cv2.BORDER_CONSTANT, 0); Rp = cv2.copyMakeBorder(Rf, 0, 0, pad, 0, cv2.BORDER_CONSTANT, 0)
    sg = cv2.StereoSGBM_create(minDisparity=dmin, numDisparities=nd, blockSize=9, P1=8 * 81, P2=32 * 81,
                               uniquenessRatio=5, speckleWindowSize=150, speckleRange=2,
                               mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)
    d = (sg.compute(Lp, Rp).astype(np.float32)[:, pad:][:, ::-1] / 16)[:, :W] + (DOFFS - S)
    # el punto correspondiente en la imagen derecha original: xR = xL - (DOFFS - d); debe caer dentro de la imagen
    u = np.arange(W)[None, :]
    xr = u - (DOFFS - d)
    valid = (d > dmin) & (d < dmin + nd - 1) & (L > 0) & (xr >= 0) & (xr < W)
    Z = np.where(valid, F * B / np.maximum(d, 1e-3), 0)
    return Z, valid
def to_points(Z, valid, step=1):
    v, u = np.nonzero(valid[::step, ::step]); v *= step; u *= step
    z = Z[v, u]; return np.c_[(u - CX_L) * z / F, (v - CY) * z / F, z].astype(np.float32)
def save_ply(path, pts, colors=None):
    with open(path, 'wb') as fh:
        hdr = f'ply\nformat binary_little_endian 1.0\nelement vertex {len(pts)}\nproperty float x\nproperty float y\nproperty float z\n'
        if colors is not None: hdr += 'property uchar red\nproperty uchar green\nproperty uchar blue\n'
        fh.write((hdr + 'end_header\n').encode())
        if colors is None: fh.write(pts.tobytes())
        else:
            rec = np.zeros(len(pts), dtype=[('p', '<f4', 3), ('c', 'u1', 3)]); rec['p'] = pts; rec['c'] = colors; fh.write(rec.tobytes())
if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]
    L, R, n = load_pair(src, 8)
    Z, valid = depth(L, R)
    zv = Z[valid]
    print(f'{src}: {n} pairs, valid {valid.mean()*100:.1f}%, Z p5 {np.percentile(zv,5):.0f} median {np.median(zv):.0f} p95 {np.percentile(zv,95):.0f} mm')
    os.makedirs(out, exist_ok=True)
    zc = np.clip((Z - 250) / (450 - 250), 0, 1)
    vis = cv2.applyColorMap((255 - zc * 255).astype(np.uint8), cv2.COLORMAP_TURBO); vis[~valid] = 0
    ir = cv2.cvtColor(cv2.normalize(L, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    cv2.imwrite(f'{out}/depth_view.png', np.hstack([cv2.resize(ir, (640, 400)), cv2.resize(vis, (640, 400))]))
    pts = to_points(Z, valid)
    g = cv2.normalize(L, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)[valid]
    save_ply(f'{out}/cloud.ply', pts, np.repeat(g[:, None], 3, 1))
    np.save(f'{out}/Z.npy', Z.astype(np.float32))
    print('saved', f'{out}/depth_view.png', f'{out}/cloud.ply', len(pts), 'points')
