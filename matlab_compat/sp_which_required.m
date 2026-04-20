function found = sp_which_required(exe)
%SP_WHICH_REQUIRED Like sp_which, but throws if the executable is missing.
%   P = SP_WHICH_REQUIRED(EXE) returns the absolute path to EXE on PATH,
%   or throws StaMPS:sp_which:notFound if the executable cannot be located.
%
%   Use sp_which_required at call-sites that CANNOT proceed without the
%   binary; use sp_which at call-sites that have a fall-back strategy
%   (e.g. "use triangle if available, else use an in-MATLAB algorithm").
%
%   See also: sp_which
    found = sp_which(exe);
    if isempty(found)
        error('StaMPS:sp_which:notFound', ...
              'sp_which_required: executable ''%s'' not found on PATH', exe);
    end
end
