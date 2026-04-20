function found = sp_which(exe)
%SP_WHICH Cross-platform 'which' for resolving executables on PATH.
%   P = SP_WHICH(EXE) returns the absolute path to EXE, searching $PATH
%   with Windows PATHEXT handling.
%
%   Contract:
%     not-found -> '' (empty string). No error is raised.
%     Callers that treat "missing binary" as a hard error should use
%     sp_which_required(EXE) instead, which throws StaMPS:sp_which:notFound.
%
%   Implementation is pure-MATLAB (no subprocess) so it is safe to call
%   from inside test doubles that override system()/!shell.
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
