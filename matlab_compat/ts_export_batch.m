function ts_export_batch(matfile, points_csv, outdir, default_radius, name_prefix)
%TS_EXPORT_BATCH Headless time-series exporter for StaMPS PSI workdirs.
%   ts_export_batch(MATFILE, POINTS_CSV, OUTDIR, DEFAULT_RADIUS) loads
%   ph_mm/lonlat/day from MATFILE (a ps_plot_ts_*.mat written by
%   ts_flaghelper), reads query points from POINTS_CSV (cols id,lon,lat
%   with optional 4th col radius_m), and writes one
%   <OUTDIR>/ts_<id>.csv per point with cols {date, disp_mm}.
%
%   ts_export_batch(..., NAME_PREFIX) overrides the 'ts' prefix in the
%   output filename, so each point lands as <OUTDIR>/<NAME_PREFIX>_<id>.csv.
%   Used by the picker to keep the per-point files in sync with the
%   PHASE_StaMPS "Filename" field (legacy STEP 3 export).
%
%   Replaces the interactive ginput flow of ts_plot.m for batch / GUI
%   driven workflows where the points are known a priori.
%
%   Requires StaMPS/matlab on the path for llh2local.

    narginchk(4, 5);
    if nargin < 5 || isempty(name_prefix)
        name_prefix = 'ts';
    end

    if ~isfolder(outdir)
        mkdir(outdir);
    end

    required = {'ph_mm', 'lonlat', 'day'};
    present  = {whos('-file', matfile).name};
    missing  = required(~ismember(required, present));
    if ~isempty(missing)
        error('ts_export_batch:badMat', ...
              'matfile %s is missing required variable(s): %s', ...
              matfile, strjoin(missing, ', '));
    end
    S = load(matfile, 'ph_mm', 'lonlat', 'day');
    ph_mm  = S.ph_mm;
    lonlat = S.lonlat;
    day    = S.day;

    P = read_points_csv(points_csv);

    for k = 1:height(P)
        id   = P.id(k);
        lon0 = P.lon(k);
        lat0 = P.lat(k);
        if ismember('radius_m', P.Properties.VariableNames) && ...
                ~isnan(P.radius_m(k))
            r = P.radius_m(k);
        else
            r = default_radius;
        end

        % Use StaMPS' own ellipsoidal local projection so radius semantics
        % match ts_plot.m:55 exactly.
        xy = llh2local(lonlat', [lon0; lat0])' * 1000;
        in = (xy(:,1).^2 + xy(:,2).^2) <= r^2;

        if ~any(in)
            warning('ts_export_batch:noPS', ...
                    'point %s: no PS within %g m of (%g,%g)', ...
                    id, r, lon0, lat0);
            continue;
        end

        ts_mean = mean(ph_mm(in,:), 1).';
        date_str = cellstr(string(datetime(day(:), ...
                           'ConvertFrom', 'datenum'), 'yyyy-MM-dd'));

        T = table(date_str, ts_mean, ...
                  'VariableNames', {'date', 'disp_mm'});
        writetable(T, fullfile(outdir, sprintf('%s_%s.csv', name_prefix, id)));
    end
end


function P = read_points_csv(points_csv)
    opts = detectImportOptions(points_csv, 'TextType', 'string');

    required = {'id', 'lon', 'lat'};
    missing  = required(~ismember(required, opts.VariableNames));
    if ~isempty(missing)
        error('ts_export_batch:badCsv', ...
              'CSV %s is missing required column(s): %s', ...
              points_csv, strjoin(missing, ', '));
    end

    opts = setvartype(opts, 'id', 'string');
    P = readtable(points_csv, opts);

    P.id = sanitise_ids(P.id);

    [u, iu] = unique(P.id, 'stable');
    if numel(u) ~= numel(P.id)
        dupe = P.id(setdiff(1:numel(P.id), iu));
        error('ts_export_batch:duplicateId', ...
              'CSV has duplicate id(s): %s', strjoin(dupe, ', '));
    end
end


function ids = sanitise_ids(ids)
    bad_chars = '/\:*?"<>| ';
    for k = 1:numel(ids)
        s = char(ids(k));
        if isempty(s)
            error('ts_export_batch:emptyId', ...
                  'CSV row %d has an empty id', k);
        end
        s(ismember(s, bad_chars)) = '_';
        ids(k) = string(s);
    end
end
