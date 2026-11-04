calibration_moments = ...
@(m, par) [  mean(m.rf - m.rd), ...    % Moment 1: average value of the liquidity premium spread. 
    m.credit_spread_change_in_crises_avg, ...   % Moment 2: the change of credit spread during a crisis. Since credit spread is normalized, the result can be interpretd as a percentage. 
    calculate_half_life(-m.average_path.credit_spread, par.dt), ... % Moment 3: credit spread recovery half life.
    m.output_to_capital_ratio_avg, ...  % Moment 4: output to capital ratio, to match AH+AL
    mean(m.output_change_3_years), ... % Moment 5: average output decline in crises, to match AH-AL
    m.output_growth_vol, ... % Moment 6: average output growth volatility, to match sigmaK
    m.bank_lvg_avg,  ...  % Moment 7: average bank leverage. 
    m.reg_spread_too_low_with_control.Coefficients.Estimate(2,1) / std(m.credit_spread) , ...   % Moment 8: credit spread on pre-crisis indicator
    m.reg_output_disaster_and_froth.Coefficients.Estimate(2,1), ...   % Moment 1': output disaster response to credit froth    
    m.reg_conditional_output_and_pre_crisis_spread.Coefficients.Estimate(2,1), ... % Moment 2: output growth response to pre-crisis credit spread
    m.reg_conditional_output_and_spread_spike.Coefficients.Estimate(2,1), ...  % Moment 3: output conditional response to credit spread spike
    min(m.output_change_3_years) ,  ... % Moment 4: minimum of output growth in 3 years after crises. 
    m.reg_bank_equity_excess_return_and_bank_credit.Coefficients.Estimate(2,1), ...   % Moment 5: excess bank equity return and bank credit regression coefficients.
    m.bank_equity_excess_return_on_high_credit, ...  % Moment 6: excess capital return conditional on high bank credit. 
    m.frequency_distress_simulated , ...                         % Moment 7: average frequency of the liquidity shocks
    mean(m.RK_monthly*12 - m.rd) , ...   % Moment 8: the mean net interest rate margins. 
    m.reg_bank_credit_predicting_crash(2), ...   % Moment 9: bank credit predicting equity crash
    m.reg_spread_pre_crash.Coefficients.Estimate(2,1)  ...   % Moment 10: credit spread before equity crashes. 
    m.frequency_non_sparse_crisis  ...    % Moment 11: frequency of non-sparse crises
    m.frequency_non_sparse_equity_crashes  ...    % Moment 12: frequency of non-sparse equity crashes
    ];




