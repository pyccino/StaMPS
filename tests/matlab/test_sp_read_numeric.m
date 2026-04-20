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
        function reads_scientific_notation(tc)
            fp = fullfile(tc.TmpDir, 's.in');
            fid = fopen(fp, 'w'); fprintf(fid, '1.5e-3 2.5E+4\n'); fclose(fid);
            vals = sp_read_numeric(fp);
            tc.verifyEqual(vals(1), 1.5e-3, 'AbsTol', 1e-12);
            tc.verifyEqual(vals(2), 2.5e4,  'AbsTol', 1e-6);
        end
        function reads_crlf_file(tc)
            % Simulate a Windows-authored file with CRLF terminators.
            fp = fullfile(tc.TmpDir, 'crlf.in');
            fid = fopen(fp, 'w'); fwrite(fid, sprintf('10.5\r\n20.25\r\n')); fclose(fid);
            tc.verifyEqual(sp_read_numeric(fp), [10.5; 20.25]);
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
