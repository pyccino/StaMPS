classdef test_sp_which < matlab.unittest.TestCase
    methods (Test)
        function test_finds_matlab(tc)
            % MATLAB itself is on PATH when this test runs.
            tc.verifyNotEmpty(sp_which('matlab'));
        end

        function test_nonexistent_returns_empty(tc)
            tc.verifyEqual(sp_which('this-binary-name-does-not-exist-anywhere'), '');
        end

        function test_extension_trial_windows(tc)
            tc.assumeTrue(ispc, 'Windows-only test');
            % Worker creates fixture dir tests/matlab/fixtures/path_ext/ with
            % foo.exe, bar.bat, baz.cmd, then prepends to PATH.
            fdir = fullfile(fileparts(mfilename('fullpath')), 'fixtures', 'path_ext');
            tc.assumeTrue(exist(fdir, 'dir') == 7, sprintf('Fixture dir missing: %s', fdir));
            origPath = getenv('PATH');
            cleanup = onCleanup(@() setenv('PATH', origPath));
            setenv('PATH', [fdir pathsep origPath]);
            tc.verifyNotEmpty(sp_which('foo'));
            tc.verifyNotEmpty(sp_which('bar'));
            tc.verifyNotEmpty(sp_which('baz'));
        end

        function test_honors_pathext_windows(tc)
            tc.assumeTrue(ispc, 'Windows-only test');
            fdir = fullfile(fileparts(mfilename('fullpath')), 'fixtures', 'path_ext');
            tc.assumeTrue(exist(fdir, 'dir') == 7);
            % Add .com fixture and .COM to PATHEXT
            comFile = fullfile(fdir, 'foo.com');
            if ~exist(comFile, 'file'); fclose(fopen(comFile, 'w')); end
            origPath = getenv('PATH'); origExt = getenv('PATHEXT');
            cleanup = onCleanup(@() (setenv('PATH', origPath), setenv('PATHEXT', origExt)));
            setenv('PATH', [fdir pathsep origPath]);
            setenv('PATHEXT', [origExt pathsep '.COM']);
            tc.verifyNotEmpty(sp_which('foo'));
        end

        function test_case_insensitive_windows(tc)
            tc.assumeTrue(ispc, 'Windows-only test');
            % Triangle binary (built by Phase 1) is conventionally lowercase.
            fdir = fullfile(getenv('STAMPS'), 'external', 'triangle', 'bin');
            tc.assumeTrue(exist(fdir, 'dir') == 7, 'Triangle not built');
            origPath = getenv('PATH');
            cleanup = onCleanup(@() setenv('PATH', origPath));
            setenv('PATH', [fdir pathsep origPath]);
            tc.verifyEqual(sp_which('TRIANGLE'), sp_which('Triangle'));
        end

        function test_respects_path_runtime_change(tc)
            origPath = getenv('PATH');
            cleanup = onCleanup(@() setenv('PATH', origPath));
            setenv('PATH', '');
            tc.verifyEqual(sp_which('matlab'), '');
        end

        function test_returns_absolute_path(tc)
            p = sp_which('matlab');
            tc.assumeNotEmpty(p);
            % Linux/macOS: starts with '/'. Windows: drive letter or UNC.
            if ispc
                tc.verifyTrue(~isempty(regexp(p, '^([A-Za-z]:|\\\\)', 'once')), ...
                    sprintf('Expected absolute Windows path, got: %s', p));
            else
                tc.verifyEqual(p(1), '/');
            end
        end

        function test_does_not_invoke_subprocess(tc)
            % sp_which must not shell out (would be slow on Windows + recursive).
            % Spy by overriding system() locally; if invoked, set a flag.
            spy = onCleanup(@() rmpath(tempdir));
            spyDir = tempfile_dir();
            mkdir(spyDir);
            spyFile = fullfile(spyDir, 'system.m');
            fid = fopen(spyFile, 'w');
            fprintf(fid, 'function [s,o] = system(varargin)\n');
            fprintf(fid, '  error(''sp_which:invokedSystem'', ''sp_which called system()'');\n');
            fprintf(fid, 'end\n');
            fclose(fid);
            addpath(spyDir);
            cleanupSpy = onCleanup(@() (rmpath(spyDir), rmdir(spyDir, 's')));
            tc.verifyWarningFree(@() sp_which('matlab'));
        end
    end
end

function p = tempfile_dir()
    p = fullfile(tempdir, ['sp_which_test_' num2str(feature('getpid'))]);
end
