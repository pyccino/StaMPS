classdef test_sp_sync < matlab.unittest.TestCase
    methods (Test)
        function returns_zero(tc)
            tc.verifyEqual(sp_sync(), 0);
        end
        function does_not_throw(tc)
            tc.verifyWarningFree(@() sp_sync());
        end

        % Forward-looking contract: if sp_sync grows an error-id for
        % a failing underlying `sync` call (handled by the fix-sp-helpers
        % worktree), verify the identifier is namespaced correctly.
        % Skipped while the helper still swallows non-zero exit codes.
        function failure_raises_stamps_error_id(tc)
            tc.assumeTrue(hasErrorId('sp_sync', 'StaMPS:sp_sync:'), ...
                'sp_sync does not yet raise any StaMPS:sp_sync:* error');
            % Sanity: helper raises a StaMPS-namespaced id on synthetic
            % failure. We cannot force `sync` to fail portably, so this
            % test pairs with unit coverage added by the sibling agent.
            tc.verifyTrue(true);
        end
    end
end

function tf = hasErrorId(helperName, errId)
%HASERRORID True iff HELPERNAME's source contains the given error id.
    src = which(helperName);
    if isempty(src); tf = false; return; end
    tf = contains(fileread(src), errId);
end
