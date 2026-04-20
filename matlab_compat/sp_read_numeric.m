function vals = sp_read_numeric(path)
%SP_READ_NUMERIC Locale-safe replacement for load() on numeric text files.
%   Replaces load() which is locale-sensitive on Windows MATLAB.
    if ~exist(path, 'file')
        error('StaMPS:readNumeric:fileNotFound', 'File not found: %s', path);
    end
    text = fileread(path);
    text = strrep(text, char(13), '');   % strip CR
    vals = sscanf(text, '%f');
    if isempty(vals)
        error('StaMPS:readNumeric:malformed', ...
              'No numeric values found in %s', path);
    end
end
