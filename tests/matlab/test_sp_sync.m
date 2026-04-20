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
            tc.addTeardown(@() setenv('PATH', origPath));
            tc.addTeardown(@() rmdir(stubDir, 's'));
            setenv('PATH', [stubDir pathsep origPath]);
            tc.verifyError(@() sp_sync(), 'StaMPS:sp_sync:syncFailed');
        end
        function failure_id_present_in_source(tc)
            % Static source-level check complements the live stub test;
            % guards against the taxonomy id silently drifting.
            src = which('sp_sync');
            tc.assumeNotEmpty(src);
            tc.verifyTrue(contains(fileread(src), 'StaMPS:sp_sync:syncFailed'), ...
                'sp_sync source must raise StaMPS:sp_sync:syncFailed');
        end
    end
end
