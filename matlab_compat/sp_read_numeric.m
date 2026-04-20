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
%   NaN/Inf handling:
%     str2double returns NaN both for the legitimate IEEE-754 literal 'NaN'
%     AND for unparsable garbage ('abc'). To disambiguate, each token is
%     pre-validated against a regex matching the syntactic shape of a valid
%     decimal-dot number or a NaN/Inf literal; only tokens failing the
%     regex are flagged as malformed. The parsed 'NaN' literal is preserved
%     verbatim in the output vector.
%
%   Errors:
%     StaMPS:readNumeric:fileNotFound  - path does not exist
%     StaMPS:readNumeric:malformed     - file contained no parsable numbers,
%                                        or contained a token that is not a
%                                        valid numeric literal
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
    % Pre-filter each token against the syntactic shape of a valid decimal
    % number or IEEE-754 special (NaN/Inf). This sidesteps the ambiguity
    % where str2double('abc') and str2double('NaN') both return NaN. The
    % regex accepts an optional sign, a mantissa (digits with optional dot
    % or leading dot), and an optional exponent; OR the literal 'inf'/'nan'
    % (case-insensitive) with optional sign.
    number_re = '^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$|^[+-]?([iI][nN][fF]|[nN][aA][nN])$';
    for k = 1:numel(tokens)
        if isempty(regexp(tokens{k}, number_re, 'once'))
            error('StaMPS:readNumeric:malformed', ...
                  'Non-numeric token %s in %s', tokens{k}, path);
        end
    end
    vals = str2double(tokens(:));
end
