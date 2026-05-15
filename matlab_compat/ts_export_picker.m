function ts_export_picker(workdir, parent, value_type, export_name)
%TS_EXPORT_PICKER Interactive picker for time-series export points.
%   ts_export_picker(WORKDIR) opens a standalone uifigure with a
%   satellite basemap showing every PS in
%   WORKDIR/ps_plot_ts_<VALUE_TYPE>.mat coloured by a per-PS LOS-rate
%   proxy (least-squares slope of ph_mm vs time). The user clicks on
%   the map (or types coordinates manually) to add query points, edits
%   id / radius in a table, and exports per-point time-series CSVs by
%   invoking ts_export_batch under the hood.
%
%   ts_export_picker(WORKDIR, PARENT) builds the picker INSIDE PARENT
%   (e.g. a uitab in PHASE_StaMPS) instead of opening a popup figure.
%   PARENT must be a uifigure, uitab, or uipanel; existing children are
%   removed before the picker is built.
%
%   ts_export_picker(WORKDIR, PARENT, VALUE_TYPE) loads
%   ps_plot_ts_<VALUE_TYPE>.mat. Default 'v-do' (the standard PHASE
%   PSI flavour: velocity, deramped, orbit-corrected). Other StaMPS
%   value_types: 'v', 'v-d', 'v-da', 'v-dao', etc. — must match the
%   value_type passed to ps_plot('<vt>','ts',...).
%
%   ts_export_picker(WORKDIR, PARENT, VALUE_TYPE, EXPORT_NAME) writes
%   the per-point CSVs into WORKDIR/EXPORT/<EXPORT_NAME>_<id>.csv
%   (same folder and naming root as the legacy full-PS export from
%   PHASE_StaMPS STEP 3). When EXPORT_NAME is empty the picker falls
%   back to the legacy WORKDIR/ts_export/ts_<id>.csv layout.
%
%   Replaces the click-by-click ginput flow embedded in ps_plot's
%   "TS plot" pushbutton (StaMPS/matlab/ps_plot.m:2218-2238).
%
%   Requires Mapping Toolbox (geoaxes / geobasemap) and StaMPS/matlab
%   on the path (for llh2local, used inside ts_export_batch).

    if nargin < 1 || isempty(workdir)
        workdir = pwd;
    end
    if nargin < 3 || isempty(value_type)
        value_type = 'v-do';
    end
    if nargin < 4 || isempty(export_name)
        export_name = '';
    end

    if ~license('test', 'Map_Toolbox')
        error('ts_export_picker:noToolbox', ...
              ['Mapping Toolbox is required for the picker (geoaxes ' ...
               '/ geobasemap). Install it or use ts_export_batch ' ...
               'directly with a hand-written CSV.']);
    end

    matfile = fullfile(workdir, sprintf('ps_plot_ts_%s.mat', value_type));
    if ~isfile(matfile)
        % Fallback: any ps_plot_ts_*.mat in the workdir? Mention it
        % in the error so the user knows what to pass as value_type.
        candidates = dir(fullfile(workdir, 'ps_plot_ts_*.mat'));
        if ~isempty(candidates)
            other = strjoin({candidates.name}, ', ');
            error('ts_export_picker:noMat', ...
                  ['ps_plot_ts_%s.mat not found in %s. Other ' ...
                   'ps_plot_ts_*.mat files present: %s. Pass the ' ...
                   'corresponding value_type as the 3rd arg.'], ...
                  value_type, workdir, other);
        end
        error('ts_export_picker:noMat', ...
              ['ps_plot_ts_%s.mat not found in %s. Generate it by ' ...
               'running ps_plot(''%s'',''ts'',1,...) after stamps(7).'], ...
              value_type, workdir, value_type);
    end

    S = load(matfile, 'ph_mm', 'lonlat', 'day');
    if numel(unique(S.day)) < 2
        error('ts_export_picker:singleEpoch', ...
              ['matfile %s contains only one distinct epoch — ' ...
               'cannot compute LOS rate for the colour map.'], matfile);
    end
    years = (S.day(:) - S.day(1)) / 365.25;
    v_mmyr = nan(size(S.ph_mm, 1), 1);
    for k = 1:numel(v_mmyr)
        coeffs = polyfit(years, S.ph_mm(k,:)', 1);
        v_mmyr(k) = coeffs(1);
    end

    if nargin < 2 || isempty(parent)
        host = uifigure('Name', 'PHASE — TS Export Points', ...
                        'Position', [80 60 1200 720]);
    else
        host = parent;
        delete(host.Children);   % clear any placeholder content
    end
    topfig = ancestor(host, 'figure');

    state.workdir  = workdir;
    state.matfile  = matfile;
    state.lonlat   = S.lonlat;
    state.markers  = gobjects(0);
    state.selected = [];
    host.UserData = state;

    gl = uigridlayout(host, [3 2]);
    gl.RowHeight   = {30, '1x', 60};
    gl.ColumnWidth = {'2x', 380};

    wd = uilabel(gl, 'Text', sprintf('Workdir: %s', workdir), ...
                 'FontWeight', 'bold', 'Tooltip', workdir);
    wd.Layout.Row = 1; wd.Layout.Column = [1 2];

    % Wrap geoaxes in a bare uipanel: uigridlayout intercepts mouse
    % events before they reach a directly-parented geoaxes child on
    % R2026a, which kills pan/zoom. Putting an opaque container in the
    % middle restores native interactions.
    mapPanel = uipanel(gl, 'BorderType', 'none');
    mapPanel.Layout.Row = 2; mapPanel.Layout.Column = 1;
    ax = geoaxes(mapPanel);
    sc = geoscatter(ax, S.lonlat(:,2), S.lonlat(:,1), 18, v_mmyr, 'filled');
    try
        geobasemap(ax, 'satellite');
    catch
        geobasemap(ax, 'streets-light');
    end
    cb = colorbar(ax);
    cb.Label.String = 'LOS rate (linear fit) [mm/yr]';
    colormap(ax, turbo);

    hold(ax, 'on');

    % Default state: native geoaxes interactions (pan/zoom/datatip)
    % stay live so the user can navigate freely. Click-to-pick is
    % gated behind a toggle (see bPick below). Save the default
    % interaction handle once; enableDefaultInteractivity is a no-op
    % on geoaxes once Interactions has been overridden, so we restore
    % by reassignment instead.
    %
    % Click capture is done via topfig.WindowButtonDownFcn rather than
    % a ButtonDownFcn on the scatter: simply having a ButtonDownFcn
    % registered on the scatter (even with HitTest='off') is enough
    % to suppress the geoaxes default pan permanently on R2026a, and
    % clearing it doesn't fully reset.
    default_interactions = ax.Interactions;

    rPanel = uipanel(gl, 'Title', 'Selected points');
    rPanel.Layout.Row = 2; rPanel.Layout.Column = 2;
    rgl = uigridlayout(rPanel, [5 1]);
    rgl.RowHeight = {'1x', 36, 30, 30, 30};

    tbl = uitable(rgl);
    tbl.Layout.Row = 1;
    tbl.ColumnName    = {'id','lon','lat','radius_m'};
    tbl.ColumnFormat  = {'char','numeric','numeric','numeric'};
    tbl.ColumnEditable = [true true true true];
    tbl.ColumnWidth   = {90, 75, 75, 70};
    tbl.Data = empty_data();
    tbl.CellSelectionCallback = @on_cell_selected;

    bPick = uibutton(rgl, 'state', ...
        'Text', 'Pick PS mode  —  OFF (navigate)', ...
        'Tooltip', ['When ON: click on a PS dot to snap-add it. ' ...
                    'When OFF: full pan / zoom / datatip on the map.']);
    bPick.Layout.Row = 2;
    bPick.ValueChangedFcn = @on_pick_toggle;

    bAdd = uibutton(rgl, 'Text', 'Add free point (click anywhere)...');
    bAdd.Layout.Row = 3;
    bAdd.Tooltip = ['Drop a query point at the EXACT click location ' ...
                    '(not snapped to a PS). Useful to query an area ' ...
                    'where no PS sits exactly under the click — ' ...
                    'combined with a non-zero radius_m, exports the ' ...
                    'spatial mean of all PS within that radius.'];
    bAdd.ButtonPushedFcn = @on_add_click;

    bAddManual = uibutton(rgl, 'Text', 'Add manually (type coords)...');
    bAddManual.Layout.Row = 4;
    bAddManual.ButtonPushedFcn = @on_add_manual;

    bRm = uibutton(rgl, 'Text', 'Remove selected');
    bRm.Layout.Row = 5;
    bRm.ButtonPushedFcn = @on_remove;

    bPanel = uipanel(gl);
    bPanel.Layout.Row = 3; bPanel.Layout.Column = [1 2];
    bgl = uigridlayout(bPanel, [1 7]);
    bgl.ColumnWidth = {150, 80, 110, 110, 130, '1x', 90};

    uilabel(bgl, 'Text', 'New-point radius (m):', ...
            'HorizontalAlignment', 'right', ...
            'Tooltip', ['Pre-fills the radius_m column when you add a ' ...
                        'new point. Override per-row in the table.']);
    radEdit = uieditfield(bgl, 'numeric', 'Value', 100, 'Limits', [1 1e6]);

    bLoad = uibutton(bgl, 'Text', 'Load points list (CSV)');
    bLoad.Tooltip = ['Reload a previously saved selection of query ' ...
                     'points (id, lon, lat, radius_m) from a CSV. ' ...
                     'Does NOT export time-series — only repopulates ' ...
                     'the table above.'];
    bLoad.ButtonPushedFcn = @on_load;

    bSave = uibutton(bgl, 'Text', 'Save points list (CSV)');
    bSave.Tooltip = ['Save the current query points (id, lon, lat, ' ...
                     'radius_m) to a CSV file, to reuse the same ' ...
                     'selection in a later run. Does NOT export ' ...
                     'time-series.'];
    bSave.ButtonPushedFcn = @on_save;

    bRun = uibutton(bgl, 'Text', 'Run TS export', ...
                    'BackgroundColor', [0.4 0.7 0.4]);
    bRun.Tooltip = ['Extract the actual time-series CSVs for each ' ...
                    'point in the table above. Writes one file per ' ...
                    'point into the EXPORT/ folder.'];
    bRun.ButtonPushedFcn = @on_run;

    statusLabel = uilabel(bgl, 'Text', '');

    if isa(host, 'matlab.ui.Figure')
        bClose = uibutton(bgl, 'Text', 'Close');
        bClose.ButtonPushedFcn = @(~,~) close(host);
    else
        % Embedded mode: 'Close' would close the whole PHASE_StaMPS
        % window, which is not what the user wants. Hide the button.
        uilabel(bgl, 'Text', '');
    end

    autoload = fullfile(workdir, 'aoi_points.csv');
    if isfile(autoload)
        try
            load_csv_into_ui(autoload);
            statusLabel.Text = sprintf('Auto-loaded %s', autoload);
        catch ME
            statusLabel.Text = ['Auto-load failed: ' ME.message];
        end
    end

    function on_pick_toggle(src, ~)
        if src.Value
            ax.Interactions = zoomInteraction;
            topfig.WindowButtonDownFcn = @on_fig_click;
            src.Text = 'Pick PS mode  —  ON  (click PS to add)';
            src.BackgroundColor = [1 0.85 0.4];
            statusLabel.Text = ['Pick mode ON: click a PS dot to ' ...
                                'snap-add it. Toggle off to pan.'];
        else
            topfig.WindowButtonDownFcn = '';
            ax.Interactions = default_interactions;
            src.Text = 'Pick PS mode  —  OFF (navigate)';
            src.BackgroundColor = [0.96 0.96 0.96];
            statusLabel.Text = 'Navigate mode: pan/zoom/datatip enabled.';
        end
    end

    function on_fig_click(~, ~)
        cp_fig = topfig.CurrentPoint;
        ap = getpixelposition(ax, true);
        if cp_fig(1) < ap(1) || cp_fig(1) > ap(1)+ap(3) || ...
           cp_fig(2) < ap(2) || cp_fig(2) > ap(2)+ap(4)
            return;
        end
        % geoaxes CurrentPoint columns are [lat lon alt]. Same axis
        % order is used by drawpoint.Position in on_add_click below.
        cp_ax = ax.CurrentPoint;
        click_lat = cp_ax(1, 1);
        click_lon = cp_ax(1, 2);
        snap_to_nearest(click_lon, click_lat);
    end

    function snap_to_nearest(click_lon, click_lat)
        s = host.UserData;
        m_per_deg_lat = 111320;
        m_per_deg_lon = 111320 * cosd(click_lat);
        dx = (s.lonlat(:,1) - click_lon) * m_per_deg_lon;
        dy = (s.lonlat(:,2) - click_lat) * m_per_deg_lat;
        [~, idx] = min(dx.^2 + dy.^2);
        snap_lon = s.lonlat(idx, 1);
        snap_lat = s.lonlat(idx, 2);
        new_id = next_unique_id();
        append_point(new_id, snap_lon, snap_lat, radEdit.Value);
        statusLabel.Text = sprintf( ...
            'Snapped %s to PS #%d at (%.5f, %.5f)', ...
            new_id, idx, snap_lon, snap_lat);
    end

    function on_cell_selected(~, e)
        s = host.UserData;
        if isempty(e.Indices)
            s.selected = [];
        else
            s.selected = e.Indices(1);
        end
        host.UserData = s;
    end

    function on_add_click(~,~)
        statusLabel.Text = ['Click anywhere on the map to drop a free ' ...
                            'point (or click a PS directly)'];
        try
            roi = drawpoint(ax, 'Color', 'r');
        catch ME
            if startsWith(ME.identifier, 'images:roi:') || ...
                    startsWith(ME.identifier, 'MATLAB:graphics:roi:')
                statusLabel.Text = ['drawpoint cancelled: ' ME.message];
                return;
            end
            rethrow(ME);
        end
        if isempty(roi.Position)
            delete(roi);
            statusLabel.Text = 'cancelled';
            return;
        end
        % Same convention as on_fig_click: drawpoint.Position on a
        % geoaxes is [lat lon].
        pos  = roi.Position;
        lat0 = pos(1);
        lon0 = pos(2);
        delete(roi);
        append_point(next_unique_id(), lon0, lat0, radEdit.Value);
        statusLabel.Text = sprintf('Added at (%.5f, %.5f) — edit id in table', ...
                                   lon0, lat0);
    end

    function on_add_manual(~,~)
        try
            prompt_manual_entry(@(id, lon, lat, rad) ...
                append_point(id, lon, lat, rad));
        catch ME
            % Closing the modal with the [X] button (or a build-time
            % uifigure error in older/newer MATLAB) shouldn't dump a
            % stack trace into the console. Status label gets the
            % short version, picker keeps working.
            statusLabel.Text = sprintf('Manual entry cancelled: %s', ME.message);
        end
    end

    function append_point(id, lon, lat, rad)
        if isempty(rad) || isnan(rad)
            rad = radEdit.Value;
        end
        new_row = {char(id), lon, lat, rad};
        d = tbl.Data;
        if is_empty_data(d)
            tbl.Data = new_row;
        else
            tbl.Data = [d; new_row];
        end
        s = host.UserData;
        [prev_lat, prev_lon] = geolimits(ax);
        m = geoplot(ax, lat, lon, 'r*', ...
                    'MarkerSize', 12, 'LineWidth', 2);
        m.HitTest = 'off';
        m.PickableParts = 'none';
        s.markers(end+1) = m;
        geolimits(ax, prev_lat, prev_lon);
        host.UserData = s;
    end

    function on_remove(~,~)
        s = host.UserData;
        n = data_height(tbl.Data);
        if isempty(s.selected) || s.selected > n
            statusLabel.Text = 'No row selected';
            return;
        end
        idx = s.selected;
        if n == 1
            tbl.Data = empty_data();
        else
            d = tbl.Data;
            d(idx,:) = [];
            tbl.Data = d;
        end
        if idx <= numel(s.markers) && isgraphics(s.markers(idx))
            delete(s.markers(idx));
        end
        s.markers(idx) = [];
        s.selected = [];
        host.UserData = s;
        statusLabel.Text = sprintf('Removed row %d', idx);
    end

    function on_load(~,~)
        [f, p] = uigetfile({'*.csv','CSV files (*.csv)'}, ...
                           'Load points CSV', workdir);
        if isequal(f, 0), return; end
        try
            load_csv_into_ui(fullfile(p, f));
            statusLabel.Text = sprintf('Loaded %d points from %s', ...
                                       data_height(tbl.Data), f);
        catch ME
            uialert(topfig, ME.message, 'Load failed');
        end
    end

    function load_csv_into_ui(path)
        opts = detectImportOptions(path, 'TextType', 'string');

        required = {'id','lon','lat'};
        missing  = required(~ismember(required, opts.VariableNames));
        if ~isempty(missing)
            error('ts_export_picker:badCsv', ...
                  'CSV missing required column(s): %s', ...
                  strjoin(missing, ', '));
        end

        opts = setvartype(opts, 'id', 'string');
        T = readtable(path, opts);

        if ~ismember('radius_m', T.Properties.VariableNames)
            T.radius_m = nan(height(T), 1);
        end
        T = T(:, {'id','lon','lat','radius_m'});

        s = host.UserData;
        delete(s.markers(isgraphics(s.markers)));
        s.markers = gobjects(0);

        if height(T) == 0
            tbl.Data = empty_data();
        else
            tbl.Data = [cellstr(T.id), num2cell(T.lon), num2cell(T.lat), ...
                        num2cell(T.radius_m)];
            for k = 1:height(T)
                m = geoplot(ax, T.lat(k), T.lon(k), 'r*', ...
                            'MarkerSize', 12, 'LineWidth', 2);
                m.HitTest = 'off';
                m.PickableParts = 'none';
                s.markers(end+1) = m;
            end
        end
        host.UserData = s;
    end

    function on_save(~,~)
        if data_height(tbl.Data) == 0
            statusLabel.Text = 'Nothing to save';
            return;
        end
        [f, p] = uiputfile({'*.csv','CSV files (*.csv)'}, ...
                           'Save points CSV', ...
                           fullfile(workdir, 'aoi_points.csv'));
        if isequal(f, 0), return; end
        T = data_to_table(tbl.Data);
        writetable(T, fullfile(p, f));
        statusLabel.Text = sprintf('Saved %d points to %s', ...
                                   height(T), f);
    end

    function on_run(~,~)
        if data_height(tbl.Data) == 0
            statusLabel.Text = 'No points to export';
            return;
        end
        bRun.Enable = 'off';
        statusLabel.Text = 'Exporting...';
        drawnow;

        tmp = [tempname '.csv'];
        cleaner = onCleanup(@() rm_if_exists(tmp));  %#ok<NASGU>
        % Land per-point CSVs into the same EXPORT/ folder used by the
        % PHASE_StaMPS legacy "all-PS" export (STEP 3) so the user has
        % a single place to look. When no export_name is provided
        % (standalone picker invocation), fall back to ts_export/.
        if ~isempty(export_name)
            outdir = fullfile(workdir, 'EXPORT');
            name_prefix = export_name;
        else
            outdir = fullfile(workdir, 'ts_export');
            name_prefix = 'ts';
        end

        try
            T = data_to_table(tbl.Data);
            writetable(T, tmp);
            ts_export_batch(matfile, tmp, outdir, radEdit.Value, name_prefix);
            statusLabel.Text = sprintf('Exported %d series → %s', ...
                                       height(T), outdir);
        catch ME
            statusLabel.Text = ['Export failed: ' ME.message];
        end
        bRun.Enable = 'on';
    end

    function id = next_unique_id()
        existing = string.empty;
        if ~is_empty_data(tbl.Data)
            existing = string(tbl.Data(:,1));
        end
        n = 1;
        while true
            candidate = string(sprintf('P%02d', n));
            if ~any(existing == candidate)
                id = candidate;
                return;
            end
            n = n + 1;
        end
    end

    function prompt_manual_entry(on_ok)
        d = uifigure('Name', 'Add point manually', ...
                     'Position', [200 200 360 240], ...
                     'WindowStyle', 'modal', ...
                     'CloseRequestFcn', @(src,~) delete(src));
        dgl = uigridlayout(d, [5 2]);
        dgl.RowHeight = {30, 30, 30, 30, 40};
        dgl.ColumnWidth = {120, '1x'};

        uilabel(dgl, 'Text', 'id:');
        idEdit = uieditfield(dgl, 'text', 'Value', char(next_unique_id()));

        uilabel(dgl, 'Text', 'lon (deg):');
        lonEdit = uieditfield(dgl, 'numeric', 'Value', 0);

        uilabel(dgl, 'Text', 'lat (deg):');
        latEdit = uieditfield(dgl, 'numeric', 'Value', 0);

        % R2026a tightened uieditfield validation and rejects NaN as
        % an initial Value, so we pre-fill with the picker's current
        % default radius. The user can still edit the value before
        % pressing OK.
        default_rad = radEdit.Value;
        uilabel(dgl, 'Text', sprintf('radius_m (default %g):', default_rad));
        radEditM = uieditfield(dgl, 'numeric', 'Value', default_rad, ...
                               'Limits', [1 1e6]);

        bgl2 = uigridlayout(dgl, [1 2]);
        bgl2.Layout.Row = 5; bgl2.Layout.Column = [1 2];

        uibutton(bgl2, 'Text', 'OK', ...
                 'BackgroundColor', [0.4 0.7 0.4], ...
                 'ButtonPushedFcn', @(~,~) ok());
        uibutton(bgl2, 'Text', 'Cancel', ...
                 'ButtonPushedFcn', @(~,~) close(d));

        function ok()
            id  = strtrim(idEdit.Value);
            lon = lonEdit.Value;
            lat = latEdit.Value;
            rad = radEditM.Value;
            if isempty(id)
                uialert(d, 'id cannot be empty', 'Invalid input');
                return;
            end
            if lon < -180 || lon > 180
                uialert(d, 'lon must be in [-180, 180]', 'Invalid input');
                return;
            end
            if lat < -90 || lat > 90
                uialert(d, 'lat must be in [-90, 90]', 'Invalid input');
                return;
            end
            close(d);
            on_ok(id, lon, lat, rad);
            statusLabel.Text = sprintf('Added %s manually at (%.5f, %.5f)', ...
                                       id, lon, lat);
        end
    end
end


function d = empty_data()
    d = cell(0, 4);
end


function tf = is_empty_data(d)
    tf = isempty(d) || size(d, 1) == 0;
end


function n = data_height(d)
    if is_empty_data(d)
        n = 0;
    else
        n = size(d, 1);
    end
end


function T = data_to_table(d)
    ids = string(d(:,1));
    lon = cell2mat(d(:,2));
    lat = cell2mat(d(:,3));
    rad = cell2mat(d(:,4));
    T = table(ids, lon, lat, rad, ...
              'VariableNames', {'id','lon','lat','radius_m'});
end


function rm_if_exists(path)
    if isfile(path)
        delete(path);
    end
end
