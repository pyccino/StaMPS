classdef test_sp_read_numeric < matlab.unittest.TestCase
    properties
        TmpDir
    end
    methods (TestMethodSetup)
        function makeTmp(tc)
            tc.TmpDir = tempname(); mkdir(tc.TmpDir);
        end
    end
    methods (TestMethodTeardown)
        function rmTmp(tc)
            if exist(tc.TmpDir, 'dir'); rmdir(tc.TmpDir, 's'); end
        end
    end
    methods (Test)
        function reads_single_float(tc)
            fp = fullfile(tc.TmpDir, 'h.in');
            fid = fopen(fp, 'w'); fprintf(fid, '190.456723\n'); fclose(fid);
            tc.verifyEqual(sp_read_numeric(fp), 190.456723, 'AbsTol', 1e-6);
        end
        function reads_multi_value_vector(tc)
            fp = fullfile(tc.TmpDir, 'v.in');
            fid = fopen(fp, 'w'); fprintf(fid, '1 2 3 4\n'); fclose(fid);
            tc.verifyEqual(sp_read_numeric(fp), [1; 2; 3; 4]);
        end
        function nonexistent_throws(tc)
            tc.verifyError(@() sp_read_numeric('nope.in'), ...
                           'StaMPS:readNumeric:fileNotFound');
        end
        function malformed_throws(tc)
            fp = fullfile(tc.TmpDir, 'bad.in');
            fid = fopen(fp, 'w'); fprintf(fid, 'not a number\n'); fclose(fid);
            tc.verifyError(@() sp_read_numeric(fp), 'StaMPS:readNumeric:malformed');
        end
    end
end
