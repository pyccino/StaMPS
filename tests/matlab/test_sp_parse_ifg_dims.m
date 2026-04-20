classdef test_sp_parse_ifg_dims < matlab.unittest.TestCase
    properties
        TmpDir
    end
    methods (TestMethodSetup)
        function makeTmp(tc)
            tc.TmpDir = tempname();
            mkdir(tc.TmpDir);
        end
    end
    methods (TestMethodTeardown)
        function rmTmp(tc)
            if exist(tc.TmpDir, 'dir'); rmdir(tc.TmpDir, 's'); end
        end
    end
    methods (Test)
        function parses_integer_after_key(tc)
            fp = fullfile(tc.TmpDir, 't.par');
            fid = fopen(fp, 'w'); fprintf(fid, 'azimuth_lines: 1500\n'); fclose(fid);
            tc.verifyEqual(sp_parse_ifg_dims(fp, 'azimuth_lines'), 1500);
        end
        function parses_scientific_notation(tc)
            fp = fullfile(tc.TmpDir, 't.par');
            fid = fopen(fp, 'w'); fprintf(fid, 'prf: 1.234e+03\n'); fclose(fid);
            tc.verifyEqual(sp_parse_ifg_dims(fp, 'prf'), 1234, 'AbsTol', 0.001);
        end
        function missing_key_returns_nan(tc)
            fp = fullfile(tc.TmpDir, 't.par');
            fid = fopen(fp, 'w'); fprintf(fid, 'other: 5\n'); fclose(fid);
            tc.verifyTrue(isnan(sp_parse_ifg_dims(fp, 'nothing')));
        end
        function missing_key_strict_throws(tc)
            fp = fullfile(tc.TmpDir, 't.par');
            fid = fopen(fp, 'w'); fprintf(fid, 'other: 5\n'); fclose(fid);
            tc.verifyError(@() sp_parse_ifg_dims(fp, 'nothing', 'Strict', true), ...
                           'StaMPS:parseIfgDims:keyNotFound');
        end
        function nonexistent_file_throws(tc)
            tc.verifyError(@() sp_parse_ifg_dims('nope.par', 'k'), ...
                           'StaMPS:parseIfgDims:fileNotFound');
        end
    end
end
