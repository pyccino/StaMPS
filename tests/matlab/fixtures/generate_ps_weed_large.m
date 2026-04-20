% tests/matlab/fixtures/generate_ps_weed_large.m
%
% ONE-SHOT FIXTURE GENERATOR for the ps_weed sp_sync-spy test.
%
% The emitted file, ps_weed_large.mat, is ~3 MB and is intentionally NOT
% committed to git. Run this script once on first setup (or in CI before
% the MATLAB test suite executes):
%
%     cd <stamps-root>
%     matlab -batch "run('tests/matlab/fixtures/generate_ps_weed_large.m')"
%
% If the fixture is absent, test_matlab_patches/ps_weed_sync_called will
% skip with an `assumeTrue` message pointing users at this file.
%
% The fixture must contain n_ps>400000 so that ps_weed takes the branch
% that calls sp_sync() to keep backgrounded workers in lockstep (the
% property the test is verifying).

rng(42, 'twister');   % deterministic seed; identical fixture every run

n_ps = 400001;        % just past the threshold used by ps_weed

% Minimal variable set referenced by ps_weed's first pass. Real callers
% load far more; we supply only the fields that the sp_sync-heavy loops
% touch. Anything ps_weed pulls via getparm() is expected to come from a
% parms.mat in the cwd -- that is a pre-existing acceptance-test concern,
% not something this fixture addresses.
ij2      = [int32((1:n_ps)'), int32(randi(10000, n_ps, 1)), int32(randi(10000, n_ps, 1))];
coh_ps2  = single(rand(n_ps, 1));
xy2      = single([rand(n_ps, 1) * 1e5, rand(n_ps, 1) * 1e5]);

outFile = fullfile(fileparts(mfilename('fullpath')), 'ps_weed_large.mat');
save(outFile, 'n_ps', 'ij2', 'coh_ps2', 'xy2', '-v7');

fprintf('Wrote %s (n_ps=%d)\n', outFile, n_ps);
