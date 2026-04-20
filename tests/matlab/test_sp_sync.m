classdef test_sp_sync < matlab.unittest.TestCase
    methods (Test)
        function returns_zero(tc)
            tc.verifyEqual(sp_sync(), 0);
        end
        function does_not_throw(tc)
            tc.verifyWarningFree(@() sp_sync());
        end

        % sp_sync raises StaMPS:sp_sync:syncFailed when system('sync')
        % returns a non-zero exit code. We cannot force `sync` to fail
        % portably (it's a POSIX syscall with near-100% success rate), so
        % this test confirms the id is present in the helper's source.
        % Pair with the fix-sp-helpers worktree's injected-failure unit
        % test for live coverage of the throw path.
        function failure_id_present_in_source(tc)
            src = which('sp_sync');
            tc.assumeNotEmpty(src);
            tc.verifyTrue(contains(fileread(src), 'StaMPS:sp_sync:syncFailed'), ...
                'sp_sync source must raise StaMPS:sp_sync:syncFailed');
        end
    end
end
