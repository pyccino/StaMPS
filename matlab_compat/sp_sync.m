function status = sp_sync()
%SP_SYNC No-op on Windows; delegates to `sync` on Unix.
    if ispc
        status = 0;
    else
        status = system('sync');
    end
end
