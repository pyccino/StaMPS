function found = sp_which(exe)
%SP_WHICH Cross-platform 'which' for resolving executables on PATH.
%   P = SP_WHICH(EXE) returns the absolute path to EXE, searching $PATH
%   with Windows PATHEXT handling. Returns '' if not found.
    paths = strsplit(getenv('PATH'), pathsep);
    if ispc
        pathext = strsplit(getenv('PATHEXT'), pathsep);
        exts = [{''}, pathext];
    else
        exts = {''};
    end
    for i = 1:numel(paths)
        if isempty(paths{i}); continue; end
        for j = 1:numel(exts)
            candidate = fullfile(paths{i}, [exe exts{j}]);
            if exist(candidate, 'file') == 2
                found = candidate;
                return
            end
        end
    end
    found = '';
end
