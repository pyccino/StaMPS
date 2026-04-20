function status = sp_sync()
%SP_SYNC Flush dirty filesystem buffers; cross-platform.
%   Unix:    invokes system('sync') and propagates its exit status. On
%            non-zero exit, throws StaMPS:sp_sync:syncFailed.
%   Windows: no-op (NTFS flushes on close/unmap; there is no user-mode
%            sync(1)-equivalent primitive, and FlushFileBuffers operates
%            per-handle, not globally). Returns 0.
    if ispc
        status = 0;
        return
    end
    status = system('sync');
    if status ~= 0
        error('StaMPS:sp_sync:syncFailed', ...
              'sp_sync: system(''sync'') returned rc=%d', status);
    end
end
