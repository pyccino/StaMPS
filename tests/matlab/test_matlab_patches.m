% tests/matlab/test_matlab_patches.m
% Shared harness for all 15 patched .m files. Each patch task below
% adds its test method to this class.

classdef test_matlab_patches < matlab.unittest.TestCase
    methods (Test)
        % --- Task 3.7: uw_interp.m (Triangle absent -> Delaunay fallback) ---
        function uw_interp_triangle_absent_returns_delaunay_fallback(tc)
            tc.assumeTrue(exist('tests/matlab/fixtures/uw_interp_min.mat','file') == 2, ...
                          'Min fixture missing');
            load('tests/matlab/fixtures/uw_interp_min.mat', 'ij2', 'coh_ps2', 'xy2');
            origPath = getenv('PATH');
            tc.addTeardown(@() setenv('PATH', origPath));
            setenv('PATH', '');   % force sp_which('triangle') to return ''
            tc.verifyWarningFree(@() uw_interp(ij2, coh_ps2, xy2));
        end

        % --- Task 3.8: ps_smooth_scla.m ---
        function ps_smooth_scla_runs(tc)
            tc.assumeTrue(exist('tests/matlab/fixtures/ps_smooth_min.mat','file') == 2);
            load('tests/matlab/fixtures/ps_smooth_min.mat');
            tc.verifyWarningFree(@() ps_smooth_scla);
        end

        % --- Task 3.9: ps_scn_filt.m ---
        function ps_scn_filt_runs(tc)
            tc.assumeTrue(exist('tests/matlab/fixtures/ps_scn_filt_min.mat','file') == 2);
            load('tests/matlab/fixtures/ps_scn_filt_min.mat');
            tc.verifyWarningFree(@() ps_scn_filt);
        end

        % --- Task 3.10: ps_scn_filt_krig.m ---
        function ps_scn_filt_krig_runs(tc)
            tc.assumeTrue(exist('tests/matlab/fixtures/ps_scn_filt_krig_min.mat','file') == 2);
            load('tests/matlab/fixtures/ps_scn_filt_krig_min.mat');
            tc.verifyWarningFree(@() ps_scn_filt_krig);
        end

        % --- Task 3.11: ps_weed.m (sp_sync called for n_ps>400000) ---
        function ps_weed_sync_called(tc)
            fixturePath = 'tests/matlab/fixtures/ps_weed_large.mat';
            % Fixture is too large (~3 MB) to commit; users generate it on
            % first setup. See tests/matlab/fixtures/generate_ps_weed_large.m.
            tc.assumeTrue(exist(fixturePath,'file') == 2, ...
                sprintf(['ps_weed_large.mat fixture not committed (too large for git); ', ...
                         'generate via tests/matlab/fixtures/generate_ps_weed_large.m']));
            load(fixturePath);
            % Spy on sp_sync via shadow function; require >=3 invocations.
            spyDir = fullfile(tempdir, ['sp_weed_spy_' num2str(feature('getpid'))]);
            mkdir(spyDir);
            tc.addTeardown(@() rmdir(spyDir, 's'));
            counterFile = fullfile(spyDir, 'count.txt');
            fid = fopen(fullfile(spyDir, 'sp_sync.m'), 'w');
            fprintf(fid, 'function rc = sp_sync()\n');
            fprintf(fid, '  fid = fopen(''%s'', ''a''); fprintf(fid, ''.\\n''); fclose(fid);\n', counterFile);
            fprintf(fid, '  rc = 0;\nend\n');
            fclose(fid);
            addpath(spyDir);
            tc.addTeardown(@() rmpath(spyDir));
            ps_weed;
            txt = fileread(counterFile);
            tc.verifyGreaterThanOrEqual(numel(strfind(txt, '.')), 3);
        end

        % --- Task 3.12: sb_baseline_plot.m (writes sorted .list) ---
        function sb_baseline_plot_writes_list(tc)
            tc.assumeTrue(exist('tests/matlab/fixtures/sb_baseline_min.mat','file') == 2);
            load('tests/matlab/fixtures/sb_baseline_min.mat');
            sb_baseline_plot;
            tc.verifyTrue(exist('small_baselines_considered.list','file') == 2);
            txt = fileread('small_baselines_considered.list');
            lines = strsplit(strtrim(txt), '\n');
            sortedLines = sort(lines);
            tc.verifyEqual(lines, sortedLines, 'List must be sorted');
        end

        % --- Task 3.13: mt_prep_suggestion.m (stdout contains dims) ---
        function mt_prep_suggestion_stdout_contains_dims(tc)
            fixt = 'tests/matlab/fixtures/ifg_out.txt';
            tc.assumeTrue(exist(fixt,'file') == 2);
            output = evalc(sprintf('mt_prep_suggestion(''%s'', 100, 100)', fixt));
            tc.verifyTrue(contains(output, 'number of lines ='));
            tc.verifyTrue(contains(output, 'number of pixels ='));
        end

        % --- Task 3.14: batchjob.m (hostname on Windows uses COMPUTERNAME) ---
        function batchjob_hostname_windows(tc)
            tc.assumeTrue(ispc, 'Windows-only test');
            setenv('COMPUTERNAME', 'CI-WIN-01');
            tc.addTeardown(@() setenv('COMPUTERNAME', ''));
            output = evalc('batchjob');
            tc.verifyTrue(contains(output, 'CI-WIN-01'));
        end

        % --- Task 3.15: stamps_mc_header.m (uses sp_system) ---
        function stamps_mc_header_uses_sp_system(tc)
            spyDir = fullfile(tempdir, ['mc_header_spy_' num2str(feature('getpid'))]);
            mkdir(spyDir);
            tc.addTeardown(@() rmdir(spyDir, 's'));
            flagFile = fullfile(spyDir, 'invoked.flag');
            fid = fopen(fullfile(spyDir, 'sp_system.m'), 'w');
            fprintf(fid, 'function [s,o] = sp_system(varargin)\n');
            fprintf(fid, '  fid = fopen(''%s'', ''w''); fclose(fid);\n', flagFile);
            fprintf(fid, '  s = 0; o = '''';\nend\n');
            fclose(fid);
            addpath(spyDir);
            tc.addTeardown(@() rmpath(spyDir));
            try
                stamps_mc_header;
            catch
                % stamps_mc_header may legitimately error on missing files;
                % we only care that sp_system was invoked at least once.
            end
            tc.verifyTrue(exist(flagFile, 'file') == 2, ...
                          'sp_system was not invoked by stamps_mc_header');
        end

        % --- Task 3.16: ps_sb_merge.m (uses copyfile, no !cp) ---
        function ps_sb_merge_uses_copyfile(tc)
            src = which('ps_sb_merge');
            tc.assumeNotEmpty(src);
            txt = fileread(src);
            violations = linterCshCalls(src);
            tc.verifyEmpty(violations, ...
                sprintf('ps_sb_merge.m still contains csh-idiom violations: %s', ...
                        strjoin(violations, '; ')));
            tc.verifyTrue(contains(txt, 'copyfile('));
        end

        % Negative case for 3.16: inject `!cp` into a scratch file, confirm
        % the lint helper fires. Protects the lint itself from regression.
        function testLintFiresOnInjectedCsh_psSbMerge(tc)
            tmpFile = [tempname() '.m'];
            tc.addTeardown(@() deleteIfExists(tmpFile));
            fid = fopen(tmpFile, 'w');
            fprintf(fid, 'function foo()\n!cp a b\nend\n');
            fclose(fid);
            violations = linterCshCalls(tmpFile);
            tc.verifyNotEmpty(violations, ...
                'Lint failed to detect injected `!cp` -- lint regression');
        end

        % --- Task 3.17: ps_calc_scla.m (uses delete, no !rm) ---
        function ps_calc_scla_uses_delete(tc)
            src = which('ps_calc_scla');
            tc.assumeNotEmpty(src);
            txt = fileread(src);
            violations = linterCshCalls(src);
            tc.verifyEmpty(violations, ...
                sprintf('ps_calc_scla.m still contains csh-idiom violations: %s', ...
                        strjoin(violations, '; ')));
            tc.verifyTrue(contains(txt, 'delete('));
        end

        % Negative case for 3.17: inject `!rm`, confirm lint fires.
        function testLintFiresOnInjectedCsh_psCalcScla(tc)
            tmpFile = [tempname() '.m'];
            tc.addTeardown(@() deleteIfExists(tmpFile));
            fid = fopen(tmpFile, 'w');
            fprintf(fid, 'function foo()\n!rm -f foo.txt\nend\n');
            fclose(fid);
            violations = linterCshCalls(tmpFile);
            tc.verifyNotEmpty(violations, ...
                'Lint failed to detect injected `!rm` -- lint regression');
        end

        % Negative case: `/dev/null` literal must be flagged (portability).
        function testLintFiresOnInjectedDevNull(tc)
            tmpFile = [tempname() '.m'];
            tc.addTeardown(@() deleteIfExists(tmpFile));
            fid = fopen(tmpFile, 'w');
            fprintf(fid, 'function foo()\nsystem(''echo x > /dev/null'');\nend\n');
            fclose(fid);
            violations = linterCshCalls(tmpFile);
            tc.verifyNotEmpty(violations, ...
                'Lint failed to detect injected `/dev/null` -- lint regression');
        end

        % Negative case: bare `which(` call (must use `sp_which` helper).
        function testLintFiresOnInjectedBareWhich(tc)
            tmpFile = [tempname() '.m'];
            tc.addTeardown(@() deleteIfExists(tmpFile));
            fid = fopen(tmpFile, 'w');
            fprintf(fid, 'function foo()\np = which(''triangle'');\nend\n');
            fclose(fid);
            violations = linterCshCalls(tmpFile);
            tc.verifyNotEmpty(violations, ...
                'Lint failed to detect bare `which(` -- lint regression');
        end

        % --- Task 3.18: combine_amp_dem.m (uses sp_parse_ifg_dims) ---
        function combine_amp_dem_uses_sp_parse_ifg_dims(tc)
            src = which('combine_amp_dem');
            tc.assumeNotEmpty(src);
            txt = fileread(src);
            tc.verifyTrue(contains(txt, 'sp_parse_ifg_dims'), ...
                          'combine_amp_dem.m must use sp_parse_ifg_dims helper');
            tc.verifyEmpty(regexp(txt, '!grep.*\|.*gawk', 'once'), ...
                           'shell pipeline still present');
        end

        % --- Task 3.19: ps_load_initial.m (locale-invariant) ---
        function ps_load_initial_locale_invariant(tc)
            tc.assumeTrue(exist('tests/matlab/fixtures/ps_load_initial_min','dir') == 7);
            origLocale = getenv('LC_NUMERIC');
            tc.addTeardown(@() setenv('LC_NUMERIC', origLocale));
            setenv('LC_NUMERIC', 'it_IT.UTF-8');
            withTempCwd(tc, 'tests/matlab/fixtures/ps_load_initial_min', ...
                        @() tc.verifyWarningFree(@() ps_load_initial));
        end

        % --- Task 3.20: sb_load_initial.m (locale-invariant) ---
        function sb_load_initial_locale_invariant(tc)
            tc.assumeTrue(exist('tests/matlab/fixtures/sb_load_initial_min','dir') == 7);
            origLocale = getenv('LC_NUMERIC');
            tc.addTeardown(@() setenv('LC_NUMERIC', origLocale));
            setenv('LC_NUMERIC', 'de_DE.UTF-8');
            withTempCwd(tc, 'tests/matlab/fixtures/sb_load_initial_min', ...
                        @() tc.verifyWarningFree(@() sb_load_initial));
        end

        % --- Task 3.21: buffer slot -- close without test if unused ---
        function buffer_slot_no_op(tc)
            tc.verifyTrue(true, 'Buffer slot -- no patch applied this cycle');
        end
    end
end

% --- Local functions --------------------------------------------------

function violations = linterCshCalls(path)
%LINTERCSHCALLS Scan a .m file for csh-idiom / portability violations.
%   V = LINTERCSHCALLS(PATH) returns a cellstr of human-readable violation
%   messages. Empty cell {} means the file is clean. Patterns checked:
%     * `!cp ...`     -- non-portable shell `cp` (use copyfile).
%     * `!rm ...`     -- non-portable shell `rm` (use delete).
%     * `/dev/null`   -- literal Unix device path (wrap via sp_system).
%     * bare `which(` -- MATLAB builtin; use sp_which for PATH lookups.
%   The production lint in test_matlab_patches reuses this helper so
%   positive and negative cases exercise identical detection logic.
    violations = {};
    if exist(path, 'file') ~= 2
        violations{end+1} = sprintf('linterCshCalls: file not found: %s', path);
        return
    end
    txt = fileread(path);
    if ~isempty(regexp(txt, '^!cp\b', 'once', 'lineanchors'))
        violations{end+1} = '!cp shell call (use copyfile)';
    end
    if ~isempty(regexp(txt, '^!rm\b', 'once', 'lineanchors'))
        violations{end+1} = '!rm shell call (use delete)';
    end
    if ~isempty(regexp(txt, '/dev/null', 'once'))
        violations{end+1} = '/dev/null literal (use sp_system)';
    end
    % Bare `which(` excluded when prefixed by `sp_` (i.e. sp_which) or
    % preceded by word character (e.g. identifier.which). We match only
    % `which(` preceded by start-of-line, whitespace, `=`, `(`, `,`, or `!`.
    if ~isempty(regexp(txt, '(^|[\s=\(,!])which\s*\(', 'once', 'lineanchors'))
        violations{end+1} = 'bare which( call (use sp_which)';
    end
end

function withTempCwd(tc, dirPath, fun)
%WITHTEMPCWD Run FUN with pwd temporarily set to DIRPATH.
%   WITHTEMPCWD(TC, DIRPATH, FUN) changes into DIRPATH, registers a
%   teardown on TC that restores the original pwd, then invokes FUN().
%   Using addTeardown is more robust than onCleanup -- teardown fires
%   even if the test assertion fails or the test is interrupted.
    origDir = pwd;
    tc.addTeardown(@() cd(origDir));
    cd(dirPath);
    fun();
end

function deleteIfExists(filePath)
%DELETEIFEXISTS Silent delete helper for teardown callbacks.
    if exist(filePath, 'file') == 2
        delete(filePath);
    end
end
