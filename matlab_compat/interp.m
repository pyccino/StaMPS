function y = interp(x, r)
%INTERP  Upsample by integer factor (Signal Processing Toolbox compat).
%   Y = INTERP(X, R) returns an upsampled version of X by integer factor R.
%
%   Reduced-fidelity replacement for the Signal Processing Toolbox INTERP:
%   the toolbox version applies an FIR anti-imaging low-pass; this shim
%   uses linear interpolation via INTERP1, which is the only base-MATLAB
%   primitive available without the toolbox. For StaMPS' single caller
%   (ps_est_gamma_quick.m line 301, where INTERP upsamples a coarse 10-bin
%   Prand histogram to 100 bins for lookup), the linear approximation is
%   visually indistinguishable from the toolbox output: the source Prand
%   is itself a smoothed gausswin-filtered histogram, and only point
%   lookups Prand(round(coh_ps*1000)+1) are taken afterwards, not spectral
%   properties of the interpolated signal.
%
%   Preserves input orientation (row -> row, column -> column).
r = round(r);
if r < 1
    error('interp:invalidFactor', 'Interpolation factor must be >= 1.');
end
if r == 1
    y = x;
    return;
end

was_row = isrow(x);
x = x(:);
n = numel(x);
if n < 2
    y = repmat(x, r, 1);
else
    t_orig = (1:n).';
    t_new = linspace(1, n, n*r).';
    y = interp1(t_orig, x, t_new, 'linear');
end

if was_row
    y = y(:).';
end
end
