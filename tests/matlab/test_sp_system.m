classdef test_sp_system < matlab.unittest.TestCase
    methods (Test)
        function devnull_rewrite_windows(tc)
            tc.assumeTrue(ispc);
            [s, ~] = sp_system('echo hello >& /dev/null');
            tc.verifyEqual(s, 0);
        end
        function devnull_identity_linux(tc)
            tc.assumeTrue(isunix);
            [s, ~] = sp_system('echo hello > /dev/null');
            tc.verifyEqual(s, 0);
        end
        function exit_code_propagation(tc)
            if ispc
                [s, ~] = sp_system('cmd /c exit 3');
            else
                [s, ~] = sp_system('exit 3');
            end
            tc.verifyEqual(s, 3);
        end
        function empty_string_does_not_throw(tc)
            tc.verifyWarningFree(@() sp_system(''));
        end

        % sp_system raises StaMPS:sp_system:nonZeroExit when the caller
        % does not capture STATUS (nargout == 0) and the command exits
        % with a non-zero status. Capturing STATUS propagates the code
        % silently, matching system() semantics.
        function nonzero_exit_raises_stamps_error_id(tc)
            if ispc
                badCmd = 'cmd /c exit 7';
            else
                badCmd = 'false';
            end
            tc.verifyError(@() sp_system(badCmd), 'StaMPS:sp_system:nonZeroExit');
        end
    end
end
