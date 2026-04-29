function w = gausswin(N, alpha)
%GAUSSWIN  Gaussian window (Signal Processing Toolbox compat).
%   W = GAUSSWIN(N) returns an N-point Gaussian window with default alpha=2.5.
%   W = GAUSSWIN(N, ALPHA) uses the specified alpha (reciprocal of std dev).
%
%   Formula matches MATLAB Signal Processing Toolbox gausswin:
%     w(n) = exp(-0.5 * ((n - (N-1)/2) / (sigma))^2)
%     where sigma = (N-1) / (2*alpha)
%
%   Used by StaMPS clap_filt (Combined Low-pass Adaptive Phase filter).
if nargin < 2, alpha = 2.5; end
N = round(N);
if N < 1, w = []; return; end
n = (0:N-1)' - (N-1)/2;
sigma = (N-1) / (2*alpha);
if sigma == 0
    w = ones(N, 1);
else
    w = exp(-0.5 * (n / sigma).^2);
end
end
