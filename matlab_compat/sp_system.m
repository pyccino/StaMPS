function [status, out] = sp_system(cmd)
%SP_SYSTEM Cross-platform shell invocation with csh-idiom rewriting.
%   [STATUS, OUT] = SP_SYSTEM(CMD) runs CMD via MATLAB's system() and
%   returns the exit status plus captured stdout/stderr. STATUS = SP_SYSTEM(CMD)
%   is also accepted; in that case stdout is NOT captured (matches system()).
%
%   Rewrites performed on Windows (ispc==true):
%     '>& /dev/null'   -> '>NUL 2>&1'
%     '2> /dev/null'   -> '2>NUL'
%     ' > /dev/null'   -> ' >NUL'    (word-boundary match; see note below)
%
%   The /dev/null rewrites are INTENTIONALLY word-boundary-aware: the
%   pattern requires surrounding whitespace around the redirection token
%   so that a user-supplied argument that literally contains the substring
%   '/dev/null' as part of a filename is not corrupted. Matching is done
%   with '\s>\s*/dev/null\b' rather than a bare substring.
%
%   cmd.exe special-character escaping (Windows only):
%     Characters with syntactic meaning in cmd.exe (& | < > ^ ( ) !) are
%     escaped with '^' BEFORE the /dev/null rewrites are applied, so that
%     the redirection tokens injected by this function ('>NUL', '2>NUL',
%     '>NUL 2>&1') are preserved verbatim. Callers who need a literal '>'
%     inside an argument should pass it pre-escaped; we cannot disambiguate
%     user redirections from user data without a full shell parser.
%
%     The '%%' character is handled separately: cmd.exe does NOT recognise
%     '^%%' as an escape for a literal percent sign. Instead, a literal
%     percent must be written as '%%%%' (doubling). We therefore apply the
%     doubling pass LAST, after all caret-escapes and after the mask
%     tokens have been restored, so the '>NUL' redirection tokens are not
%     affected and existing carets do not get '%%'-doubled.
%
%   Errors (all on Windows and Unix):
%     StaMPS:sp_system:invocationFailed - MATLAB's system() raised a runtime
%                                         error (e.g. command not found).
%     StaMPS:sp_system:nonZeroExit      - command exited with non-zero status
%                                         AND the caller requested no return
%                                         value (nargout == 0). When the
%                                         caller captures STATUS, non-zero is
%                                         propagated silently as in system().
    if ispc
        % 1) Rewrite the well-known /dev/null redirections first, so the
        %    replacements ('>NUL', '2>NUL', '>NUL 2>&1') are treated as
        %    trusted tokens by the escaping pass below.
        cmd = regexprep(cmd, '>&\s*/dev/null\b', '>NUL 2>&1');
        cmd = regexprep(cmd, '2>\s*/dev/null\b', '2>NUL');
        cmd = regexprep(cmd, '\s>\s*/dev/null\b', ' >NUL');
        % 2) Escape cmd.exe metacharacters that were not part of the
        %    rewrites. We deliberately skip characters already inside the
        %    injected redirection tokens ('>NUL', '2>NUL', '>NUL 2>&1') by
        %    temporarily masking them.
        MASK_FULL = char(1);
        MASK_ERR  = char(2);
        MASK_OUT  = char(3);
        cmd = strrep(cmd, '>NUL 2>&1', MASK_FULL);
        cmd = strrep(cmd, '2>NUL',     MASK_ERR);
        cmd = strrep(cmd, '>NUL',      MASK_OUT);
        % Escape metacharacters in remaining (user-supplied) operands.
        % Order matters: '^' must be escaped first so we do not double-
        % escape the carets we are about to add.
        meta = {'^', '&', '|', '<', '>', '(', ')', '!'};
        for k = 1:numel(meta)
            cmd = strrep(cmd, meta{k}, ['^' meta{k}]);
        end
        % Restore the trusted redirection tokens.
        cmd = strrep(cmd, MASK_FULL, '>NUL 2>&1');
        cmd = strrep(cmd, MASK_ERR,  '2>NUL');
        cmd = strrep(cmd, MASK_OUT,  '>NUL');
        % Finally, double any literal '%' so cmd.exe emits it verbatim.
        % This MUST happen after the mask restoration so that '>NUL' tokens
        % cannot be contaminated, and after the caret-escaping so that a
        % single '%' in the user input is doubled exactly once. cmd.exe
        % does not accept '^%%' as an escape (caret is discarded inside
        % variable-expansion parsing), so '%%%%' (doubling) is the only
        % reliable way to emit a literal percent sign.
        cmd = strrep(cmd, '%', '%%');
    end
    try
        if nargout > 1
            [status, out] = system(cmd);
        else
            status = system(cmd);
            out = '';
        end
    catch ME
        throw(MException('StaMPS:sp_system:invocationFailed', ...
            'sp_system: system() raised %s: %s (cmd=%s)', ...
            ME.identifier, ME.message, cmd));
    end
    if nargout == 0 && status ~= 0
        throw(MException('StaMPS:sp_system:nonZeroExit', ...
            'sp_system: command failed with rc=%d: %s', status, cmd));
    end
end
