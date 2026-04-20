function val = sp_parse_ifg_dims(path, key, varargin)
%SP_PARSE_IFG_DIMS Extract a numeric value following a key in a text file.
%   VAL = SP_PARSE_IFG_DIMS(PATH, KEY) searches PATH for KEY and returns
%   the first numeric literal that follows it (int/float/scientific).
%   Missing key returns NaN; pass 'Strict', true to throw instead.
%
%   Locale & decimal separator:
%     The regex token pattern and the str2double conversion both expect
%     DOT-DECIMAL separators. This matches the SNAP `.par` file spec
%     (ASCII dot-decimal, by the SNAP Graph Processing documentation).
%     Parsing is locale-invariant: str2double does NOT consult the active
%     locale, so Windows MATLAB under German/Italian (comma-decimal)
%     locale still parses these files correctly.
%
%   Errors:
%     StaMPS:parseIfgDims:fileNotFound - path does not exist
%     StaMPS:parseIfgDims:keyNotFound  - strict mode and key absent
    p = inputParser;
    addParameter(p, 'Strict', false);
    parse(p, varargin{:});
    if ~exist(path, 'file')
        error('StaMPS:parseIfgDims:fileNotFound', 'File not found: %s', path);
    end
    text = fileread(path);
    % Strip UTF-8 BOM. MATLAB's fileread encoding differs by platform:
    %   - Windows MATLAB default 'native' = Windows-1252 -> BOM bytes read as
    %     char points 239, 187, 191.
    %   - Linux MATLAB default UTF-8 -> BOM decoded to single code point 65279.
    % Handle both.
    if ~isempty(text) && double(text(1)) == 65279    % Linux UTF-8 path
        text = text(2:end);
    elseif length(text) >= 3 && all(double(text(1:3)) == [239 187 191])
        text = text(4:end);                          % Windows ANSI path
    end
    escaped = regexptranslate('escape', key);
    tok = regexp(text, [escaped '.*?([-+]?\d+\.?\d*(?:[eE][-+]?\d+)?)'], ...
                 'tokens', 'once');
    if isempty(tok)
        if p.Results.Strict
            error('StaMPS:parseIfgDims:keyNotFound', 'Key not found: %s', key);
        end
        val = NaN;
        return
    end
    val = str2double(tok{1});
end
