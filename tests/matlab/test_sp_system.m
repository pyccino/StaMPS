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

        % Forward-looking contract: if sp_system grows a non-zero-exit
        % error-id (handled by the fix-sp-helpers worktree), verify the
        % identifier is namespaced correctly. Skipped while the helper
        % still returns status codes silently.
        function nonzero_exit_raises_stamps_error_id(tc)
            tc.assumeTrue(hasErrorId('sp_system', 'StaMPS:sp_system:nonZeroExit'), ...
                'sp_system does not yet raise StaMPS:sp_system:nonZeroExit');
            if ispc
                badCmd = 'cmd /c exit 7';
            else
                badCmd = 'false';
            end
            tc.verifyError(@() sp_system(badCmd), 'StaMPS:sp_system:nonZeroExit');
        end
    end
end

function tf = hasErrorId(helperName, errId)
%HASERRORID True iff HELPERNAME's source contains the given error id.
    src = which(helperName);
    if isempty(src); tf = false; return; end
    tf = contains(fileread(src), errId);
end
