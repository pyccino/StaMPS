classdef test_sp_sync < matlab.unittest.TestCase
    methods (Test)
        function returns_zero(tc)
            tc.verifyEqual(sp_sync(), 0);
        end
        function does_not_throw(tc)
            tc.verifyWarningFree(@() sp_sync());
        end
    end
end
