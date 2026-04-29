classdef test_ts_export_batch < matlab.unittest.TestCase
    % Tests for ts_export_batch — headless time-series exporter that
    % replaces the interactive ts_plot.m / ginput workflow.
    %
    % Contract under test:
    %   ts_export_batch(matfile, points_csv, outdir, default_radius)
    %     - matfile         path to ps_plot_ts_*.mat (as written by
    %                       ts_flaghelper.m: ph_mm, lonlat, day, ...)
    %     - points_csv      CSV with cols id,lon,lat[,radius_m]
    %     - outdir          where ts_<id>.csv files are written
    %     - default_radius  radius in metres when CSV has no 4th col

    properties
        tmpdir
        matfile
    end

    methods (TestMethodSetup)
        function setup_workdir(tc)
            tc.tmpdir = tempname;
            mkdir(tc.tmpdir);

            rng(0, 'twister');

            lonlat = [
                16.6000, 39.5000;   % cluster
                16.60010, 39.50005;
                16.59995, 39.50010;
                16.60005, 39.49990;
                16.60008, 39.50012;
                16.7000, 39.6000;   % outliers
                16.8000, 39.7000;
                16.5000, 39.4000;
                16.4000, 39.3000;
                16.9000, 39.8000];
            n_ps = size(lonlat, 1);

            day = [datenum(2024,7,3); datenum(2024,7,15); datenum(2024,7,27)];
            n_ifg = numel(day);

            ph_mm = randn(n_ps, n_ifg) * 0.5;
            ph_mm(1:5,:) = repmat(linspace(0, -10, n_ifg), 5, 1) + ...
                           randn(5, n_ifg) * 0.05;

            master_day = datenum(2024,7,15);
            lambda = 0.0555;
            ref_ps = 1;
            unwrap_ifg_index = 1:n_ifg;
            ifg_list = 1:n_ifg;
            bperp = zeros(n_ifg, 1);

            tc.matfile = fullfile(tc.tmpdir, 'ps_plot_ts_v-do.mat');
            save(tc.matfile, 'ph_mm', 'lonlat', 'day', 'master_day', ...
                 'lambda', 'ref_ps', 'unwrap_ifg_index', 'ifg_list', ...
                 'bperp', 'n_ps');
        end
    end

    methods (TestMethodTeardown)
        function cleanup(tc)
            if isfolder(tc.tmpdir)
                rmdir(tc.tmpdir, 's');
            end
        end
    end

    methods (Test)
        function single_point_in_cluster_writes_csv(tc)
            points_csv = tc.write_csv('aoi.csv', ...
                table("P01", 16.6001, 39.5000, ...
                      'VariableNames', {'id', 'lon', 'lat'}));
            outdir = fullfile(tc.tmpdir, 'out');

            ts_export_batch(tc.matfile, points_csv, outdir, 100);

            expected = fullfile(outdir, 'ts_P01.csv');
            tc.verifyTrue(isfile(expected));

            R = readtable(expected);
            tc.verifyEqual(height(R), 3);
            tc.verifyEqual(R.Properties.VariableNames, {'date', 'disp_mm'});
            tc.verifyLessThan(R.disp_mm(end), -8);
            tc.verifyGreaterThan(R.disp_mm(end), -12);
        end

        function multiple_points_each_get_their_own_csv(tc)
            points_csv = tc.write_csv('aoi.csv', ...
                table(["P01"; "P02"], [16.6001; 16.7000], ...
                      [39.5000; 39.6000], ...
                      'VariableNames', {'id', 'lon', 'lat'}));
            outdir = fullfile(tc.tmpdir, 'out');

            ts_export_batch(tc.matfile, points_csv, outdir, 200);

            tc.verifyTrue(isfile(fullfile(outdir, 'ts_P01.csv')));
            tc.verifyTrue(isfile(fullfile(outdir, 'ts_P02.csv')));
        end

        function per_row_radius_m_overrides_default(tc)
            points_csv = tc.write_csv('aoi.csv', ...
                table("WIDE", 16.6100, 39.5100, 50000, ...
                      'VariableNames', {'id', 'lon', 'lat', 'radius_m'}));
            outdir = fullfile(tc.tmpdir, 'out');

            ts_export_batch(tc.matfile, points_csv, outdir, 1);

            tc.verifyTrue(isfile(fullfile(outdir, 'ts_WIDE.csv')));
        end

        function point_with_no_ps_in_radius_warns_and_skips(tc)
            points_csv = tc.write_csv('aoi.csv', ...
                table("OCEAN", -30.0, 0.0, ...
                      'VariableNames', {'id', 'lon', 'lat'}));
            outdir = fullfile(tc.tmpdir, 'out');

            tc.verifyWarning(@() ts_export_batch(tc.matfile, ...
                points_csv, outdir, 100), 'ts_export_batch:noPS');

            tc.verifyFalse(isfile(fullfile(outdir, 'ts_OCEAN.csv')));
        end

        function missing_required_column_throws(tc)
            % CSV with only id and lon (no lat) must fail loudly.
            points_csv = tc.write_csv('bad.csv', ...
                table("X", 16.6, 'VariableNames', {'id', 'lon'}));
            outdir = fullfile(tc.tmpdir, 'out');

            tc.verifyError(@() ts_export_batch(tc.matfile, ...
                points_csv, outdir, 100), 'ts_export_batch:badCsv');
        end

        function missing_id_column_throws_friendly_error(tc)
            % CSV without 'id' column must raise badCsv, not the
            % low-level UnknownVarName from setvartype.
            points_csv = tc.write_csv('noid.csv', ...
                table(16.6, 39.5, 'VariableNames', {'lon', 'lat'}));
            outdir = fullfile(tc.tmpdir, 'out');

            tc.verifyError(@() ts_export_batch(tc.matfile, ...
                points_csv, outdir, 100), 'ts_export_batch:badCsv');
        end

        function corrupt_matfile_throws(tc)
            % Matfile missing ph_mm must fail with badMat, not crash
            % deep inside with cryptic struct field error.
            bad = fullfile(tc.tmpdir, 'corrupt.mat');
            lonlat = [16.6, 39.5];  %#ok<NASGU>
            day = datenum(2024,7,15);  %#ok<NASGU>
            save(bad, 'lonlat', 'day');

            points_csv = tc.write_csv('aoi.csv', ...
                table("P01", 16.6, 39.5, ...
                      'VariableNames', {'id', 'lon', 'lat'}));

            tc.verifyError(@() ts_export_batch(bad, points_csv, ...
                fullfile(tc.tmpdir, 'out'), 100), ...
                'ts_export_batch:badMat');
        end

        function duplicate_ids_throw(tc)
            points_csv = tc.write_csv('dup.csv', ...
                table(["P01"; "P01"], [16.6; 16.7], [39.5; 39.6], ...
                      'VariableNames', {'id', 'lon', 'lat'}));

            tc.verifyError(@() ts_export_batch(tc.matfile, points_csv, ...
                fullfile(tc.tmpdir, 'out'), 100), ...
                'ts_export_batch:duplicateId');
        end

        function unsafe_id_chars_are_sanitised(tc)
            % '/' and ' ' get replaced with '_' so the filename is
            % cross-platform safe.
            points_csv = tc.write_csv('unsafe.csv', ...
                table("DAM/LEFT 1", 16.6001, 39.5000, ...
                      'VariableNames', {'id', 'lon', 'lat'}));
            outdir = fullfile(tc.tmpdir, 'out');

            ts_export_batch(tc.matfile, points_csv, outdir, 100);

            tc.verifyTrue(isfile(fullfile(outdir, 'ts_DAM_LEFT_1.csv')), ...
                'expected sanitised filename ts_DAM_LEFT_1.csv');
        end
    end

    methods (Access = private)
        function p = write_csv(tc, name, T)
            p = fullfile(tc.tmpdir, name);
            writetable(T, p);
        end
    end
end
