function vals = sp_read_numeric(path)
%SP_READ_NUMERIC Locale-invariant replacement for load() on numeric text files.
%   Replaces load() and sscanf('%f'), both of which consult the active locale
%   on Windows MATLAB and therefore mis-parse ASCII-decimal input under
%   German/Italian locales (comma as decimal separator).
%
%   Implementation: splits the file on whitespace and parses each token with
%   str2double, which is locale-invariant by MATLAB spec (dot-decimal only,
%   no thousands separators). Output is a column vector, matching the
%   previous sscanf(..., '%f') shape.
%
%   Errors:
%     StaMPS:readNumeric:fileNotFound  - path does not exist
%     StaMPS:readNumeric:malformed     - file contained no parsable numbers
    if ~exist(path, 'file')
        error('StaMPS:readNumeric:fileNotFound', 'File not found: %s', path);
    end
    text = fileread(path);
    text = strrep(text, char(13), '');   % strip CR
    % Tokenise on any whitespace run. str2double handles each ASCII-decimal
    % token independently of the active locale (unlike sscanf '%f').
    tokens = regexp(text, '\S+', 'match');
    if isempty(tokens)
        error('StaMPS:readNumeric:malformed', ...
              'No numeric values found in %s', path);
    end
    vals = str2double(tokens(:));
    if any(isnan(vals))
        error('StaMPS:readNumeric:malformed', ...
              'Non-numeric token in %s', path);
    end
end
