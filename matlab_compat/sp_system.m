function [status, out] = sp_system(cmd)
%SP_SYSTEM Cross-platform shell invocation with csh-idiom rewriting.
    if ispc
        cmd = regexprep(cmd, '>&\s*/dev/null', '>NUL 2>&1');
        cmd = regexprep(cmd, '2>\s*/dev/null', '2>NUL');
        cmd = regexprep(cmd, '>\s*/dev/null', '>NUL');
    end
    if nargout > 1
        [status, out] = system(cmd);
    else
        status = system(cmd);
    end
end
