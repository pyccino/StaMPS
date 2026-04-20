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
        function nonzero_throws_when_nargout_zero(tc)
            % When the caller ignores the return value, non-zero exit
            % must surface as StaMPS:sp_system:nonZeroExit rather than
            % silently disappearing.
            if ispc
                fn = @() sp_system('cmd /c exit 3');
            else
                fn = @() sp_system('false');
            end
            tc.verifyError(fn, 'StaMPS:sp_system:nonZeroExit');
        end
        function nonzero_silent_when_status_captured(tc)
            % The throw-on-nonzero contract applies only when the caller
            % does not capture status. Capturing status preserves the
            % system() passthrough behaviour.
            if ispc
                fn = @() disp(sp_system('cmd /c exit 3'));
            else
                fn = @() disp(sp_system('false'));
            end
            tc.verifyWarningFree(fn);
        end
        function devnull_word_boundary_not_corrupted(tc)
            % A user arg that contains '/dev/null' as a substring but
            % without the leading '\s>' guard must not be rewritten.
            % We exercise the regex by calling a harmless command that
            % embeds the token as a literal filename-ish argument.
            if ispc
                % Use 'echo' so we can inspect the captured output.
                [s, out] = sp_system('echo /dev/null-file');
                tc.verifyEqual(s, 0);
                tc.verifyTrue(contains(out, '/dev/null-file'), ...
                    sprintf('Expected literal /dev/null-file in output, got: %s', out));
            else
                [s, out] = sp_system('echo /dev/null-file');
                tc.verifyEqual(s, 0);
                tc.verifyTrue(contains(out, '/dev/null-file'), ...
                    sprintf('Expected literal /dev/null-file in output, got: %s', out));
            end
        end
    end
end
