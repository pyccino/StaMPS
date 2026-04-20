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
            cleanup = onCleanup(@() setenv('PATH', origPath));
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
            tc.assumeTrue(exist('tests/matlab/fixtures/ps_weed_large.mat','file') == 2, ...
                          'Large fixture not built; create with n_ps>400000');
            load('tests/matlab/fixtures/ps_weed_large.mat');
            % Spy on sp_sync via shadow function; require >=3 invocations.
            spyDir = fullfile(tempdir, ['sp_weed_spy_' num2str(feature('getpid'))]);
            mkdir(spyDir);
            cleanup = onCleanup(@() rmdir(spyDir, 's'));
            counterFile = fullfile(spyDir, 'count.txt');
            fid = fopen(fullfile(spyDir, 'sp_sync.m'), 'w');
            fprintf(fid, 'function rc = sp_sync()\n');
            fprintf(fid, '  fid = fopen(''%s'', ''a''); fprintf(fid, ''.\\n''); fclose(fid);\n', counterFile);
            fprintf(fid, '  rc = 0;\nend\n');
            fclose(fid);
            addpath(spyDir);
            cleanupPath = onCleanup(@() rmpath(spyDir));
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
            cleanup = onCleanup(@() setenv('COMPUTERNAME', ''));
            output = evalc('batchjob');
            tc.verifyTrue(contains(output, 'CI-WIN-01'));
        end

        % --- Task 3.15: stamps_mc_header.m (uses sp_system) ---
        function stamps_mc_header_uses_sp_system(tc)
            spyDir = fullfile(tempdir, ['mc_header_spy_' num2str(feature('getpid'))]);
            mkdir(spyDir);
            cleanup = onCleanup(@() rmdir(spyDir, 's'));
            flagFile = fullfile(spyDir, 'invoked.flag');
            fid = fopen(fullfile(spyDir, 'sp_system.m'), 'w');
            fprintf(fid, 'function [s,o] = sp_system(varargin)\n');
            fprintf(fid, '  fid = fopen(''%s'', ''w''); fclose(fid);\n', flagFile);
            fprintf(fid, '  s = 0; o = '''';\nend\n');
            fclose(fid);
            addpath(spyDir);
            cleanupPath = onCleanup(@() rmpath(spyDir));
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
            tc.verifyEmpty(regexp(txt, '^!cp\b', 'once', 'lineanchors'), ...
                           'ps_sb_merge.m still contains !cp shell call');
            tc.verifyTrue(contains(txt, 'copyfile('));
        end

        % --- Task 3.17: ps_calc_scla.m (uses delete, no !rm) ---
        function ps_calc_scla_uses_delete(tc)
            src = which('ps_calc_scla');
            tc.assumeNotEmpty(src);
            txt = fileread(src);
            tc.verifyEmpty(regexp(txt, '^!rm\b', 'once', 'lineanchors'), ...
                           'ps_calc_scla.m still contains !rm shell call');
            tc.verifyTrue(contains(txt, 'delete('));
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
            cleanup = onCleanup(@() setenv('LC_NUMERIC', origLocale));
            setenv('LC_NUMERIC', 'it_IT.UTF-8');
            cd('tests/matlab/fixtures/ps_load_initial_min');
            cleanupCd = onCleanup(@() cd(fileparts(mfilename('fullpath'))));
            tc.verifyWarningFree(@() ps_load_initial);
        end

        % --- Task 3.20: sb_load_initial.m (locale-invariant) ---
        function sb_load_initial_locale_invariant(tc)
            tc.assumeTrue(exist('tests/matlab/fixtures/sb_load_initial_min','dir') == 7);
            origLocale = getenv('LC_NUMERIC');
            cleanup = onCleanup(@() setenv('LC_NUMERIC', origLocale));
            setenv('LC_NUMERIC', 'de_DE.UTF-8');
            cd('tests/matlab/fixtures/sb_load_initial_min');
            cleanupCd = onCleanup(@() cd(fileparts(mfilename('fullpath'))));
            tc.verifyWarningFree(@() sb_load_initial);
        end

        % --- Task 3.21: buffer slot -- close without test if unused ---
        function buffer_slot_no_op(tc)
            tc.verifyTrue(true, 'Buffer slot -- no patch applied this cycle');
        end
    end
end
