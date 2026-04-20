% tests/matlab/test_matlab_patches.m
% Shared harness for all 15 patched .m files. Each patch task below
% adds its test method to this class.

classdef test_matlab_patches < matlab.unittest.TestCase
    methods (Test)
        function uw_interp_triangle_absent_returns_delaunay_fallback(tc)
            % Forgotten-patch sentinel. We use verifyFail (NOT assumeTrue)
            % so a forgotten patch in Tasks 3.7-3.21 fails CI RED instead
            % of producing a quiet skip — the original assumeTrue(false)
            % silently passed the harness in green CI even when patches
            % were missing, defeating the harness's purpose.
            tc.verifyFail(['Patch test not yet implemented for uw_interp.m. ' ...
                           'Task 3.7 worker: replace this body with the ' ...
                           'concrete test from agent-reports/matlab-tests.md §2.']);
        end

        function ps_smooth_scla_runs(tc)
            tc.verifyFail(['Patch test not yet implemented for ps_smooth_scla.m. ' ...
                           'Task 3.8 worker: replace this body with the ' ...
                           'concrete test from agent-reports/matlab-tests.md §2.']);
        end

        function ps_scn_filt_runs(tc)
            tc.verifyFail(['Patch test not yet implemented for ps_scn_filt.m. ' ...
                           'Task 3.9 worker: replace this body with the ' ...
                           'concrete test from agent-reports/matlab-tests.md §2.']);
        end

        function ps_scn_filt_krig_runs(tc)
            tc.verifyFail(['Patch test not yet implemented for ps_scn_filt_krig.m. ' ...
                           'Task 3.10 worker: replace this body with the ' ...
                           'concrete test from agent-reports/matlab-tests.md §2.']);
        end

        function ps_weed_sync_called(tc)
            tc.verifyFail(['Patch test not yet implemented for ps_weed.m. ' ...
                           'Task 3.11 worker: replace this body with the ' ...
                           'concrete test from agent-reports/matlab-tests.md §2.']);
        end

        function sb_baseline_plot_writes_list(tc)
            tc.verifyFail(['Patch test not yet implemented for sb_baseline_plot.m. ' ...
                           'Task 3.12 worker: replace this body with the ' ...
                           'concrete test from agent-reports/matlab-tests.md §2.']);
        end

        function mt_prep_suggestion_stdout_contains_dims(tc)
            tc.verifyFail(['Patch test not yet implemented for mt_prep_suggestion.m. ' ...
                           'Task 3.13 worker: replace this body with the ' ...
                           'concrete test from agent-reports/matlab-tests.md §2.']);
        end

        function batchjob_hostname_windows(tc)
            tc.verifyFail(['Patch test not yet implemented for batchjob.m. ' ...
                           'Task 3.14 worker: replace this body with the ' ...
                           'concrete test from agent-reports/matlab-tests.md §2.']);
        end

        function stamps_mc_header_uses_sp_system(tc)
            tc.verifyFail(['Patch test not yet implemented for stamps_mc_header.m. ' ...
                           'Task 3.15 worker: replace this body with the ' ...
                           'concrete test from agent-reports/matlab-tests.md §2.']);
        end

        function ps_sb_merge_uses_copyfile(tc)
            tc.verifyFail(['Patch test not yet implemented for ps_sb_merge.m. ' ...
                           'Task 3.16 worker: replace this body with the ' ...
                           'concrete test from agent-reports/matlab-tests.md §2.']);
        end

        function ps_calc_scla_uses_delete(tc)
            tc.verifyFail(['Patch test not yet implemented for ps_calc_scla.m. ' ...
                           'Task 3.17 worker: replace this body with the ' ...
                           'concrete test from agent-reports/matlab-tests.md §2.']);
        end

        function combine_amp_dem_uses_sp_parse_ifg_dims(tc)
            tc.verifyFail(['Patch test not yet implemented for combine_amp_dem.m. ' ...
                           'Task 3.18 worker: replace this body with the ' ...
                           'concrete test from agent-reports/matlab-tests.md §2.']);
        end

        function ps_load_initial_locale_invariant(tc)
            tc.verifyFail(['Patch test not yet implemented for ps_load_initial.m. ' ...
                           'Task 3.19 worker: replace this body with the ' ...
                           'concrete test from agent-reports/matlab-tests.md §2.']);
        end

        function sb_load_initial_locale_invariant(tc)
            tc.verifyFail(['Patch test not yet implemented for sb_load_initial.m. ' ...
                           'Task 3.20 worker: replace this body with the ' ...
                           'concrete test from agent-reports/matlab-tests.md §2.']);
        end

        function buffer_slot_no_op(tc)
            tc.verifyFail(['Patch test not yet implemented for buffer slot. ' ...
                           'Task 3.21 worker: replace this body with the ' ...
                           'concrete test from agent-reports/matlab-tests.md §2.']);
        end
    end
end
