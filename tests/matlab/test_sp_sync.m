classdef test_sp_sync < matlab.unittest.TestCase
    methods (Test)
        function returns_zero(tc)
            tc.verifyEqual(sp_sync(), 0);
        end
        function does_not_throw(tc)
            tc.verifyWarningFree(@() sp_sync());
        end
        function unix_failure_throws(tc)
            % Inject a 'sync' stub on PATH that exits non-zero and verify
            % sp_sync surfaces the failure with its taxonomy id.
            tc.assumeTrue(isunix);
            stubDir = tempname(); mkdir(stubDir);
            stubPath = fullfile(stubDir, 'sync');
            fid = fopen(stubPath, 'w');
            fprintf(fid, '#!/bin/sh\nexit 7\n');
            fclose(fid);
            fileattrib(stubPath, '+x');
            origPath = getenv('PATH');
            cleanup = onCleanup(@() (setenv('PATH', origPath), rmdir(stubDir, 's')));
            setenv('PATH', [stubDir pathsep origPath]);
            tc.verifyError(@() sp_sync(), 'StaMPS:sp_sync:syncFailed');
        end
    end
end
