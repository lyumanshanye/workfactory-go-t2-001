%% Codes for the article "Beliefs and Financial Crises", by Arvind Krishnamurthy and Wenhao Li.
% This file generates table 1 and 2 in the paper. 
%% Set Path and Add Path (not needed if we call this file from "Main_Step1.m")
% clear all;
% mainpath = fileparts(mfilename('fullpath'));
% addpath(genpath([ mainpath, '/Codes_Model' ] ))
% cd(mainpath);

target_moment_file = [table_path,'/moment_target.xlsx']; 
target_moment_file_general_belief = [table_path,'/general_behavioral_belief_cases.xlsx'];

%% -----------------  Print Table 1 -------------------------
S = load( ['solutions/baseline_behavioral.mat' ] );  
par = S.model_sol.par; % Note: the baseline parameterse below are the same across all three models
par_names = {'\delta'; '\rho'; '\chi'; '\alpha'; '\theta' };
moment_names = {'Depreciation rate'; 'Time Discount Rate'; 'Investment Adjustment Cost'; 'Distress Illiquidity Costs';  'Diagnostic Belief Weight' };
par_values = [  100*par.delta; 100*par.rho;  par.chi;  par.alpha;  par.theta_diagnostic  ];
unit_vec = ['%'; '%'; ' '; ' '; ' '   ];
% Create table
Table1= table(par_names, par_values, unit_vec, moment_names, 'VariableNames', {'Parameters', 'Value', 'Unit', 'Moment Conditions'} ) ;
disp('----------------------------------------------------------------------------------------------------------')
disp('--------------------- Table 1: Externally-Calibrated Parameter Values ---------------------')
disp(Table1)  
% Write the table in excel. 
writetable( Table1, [table_path,'/Table1_baseline_parameters.xlsx'] );


%% -----------------  Store Calibrated Results in Excel: Table 2 and 3 -------------------------
model_list={ 'benchmark', 'rational', 'behavioral' };    column_output = {'C','D','E'};
target_values =  readtable( target_moment_file, 'Sheet',1,  'Range',  ['B3:B10'] ,'ReadVariableNames',false).Variables;
simulation_key_moments_for_parameter_calibration;
disp('----------------------------------------------------------------------------------------------------------')
disp('--------------------- Table 2: Calibrated Parameters and Target Moments (output to file "moment_target.xlsx") ---------------------')
for( iter = 1:length(model_list) )
    disp( ['*** ', model_list{iter}, ' model:'] )
    S = load( ['solutions/baseline_', model_list{iter}, '.mat' ] );
    m = simulation_results_output(S, 15000);  % the second parameter is simulation year
    calibrated_par_values = calibration_moments(m,S.model_sol.par);
    writetable( array2table(calibrated_par_values([1:8,15:16])') , target_moment_file , 'Sheet', 1,  'Range',   [ column_output{iter}, '3:',  column_output{iter}, num2str(3+length(target_values)+1) ]  ,'WriteVariableNames',false);
    par = S.model_sol.par;
    if( strcmp(model_list{iter}, 'benchmark') )
         par_values = [   par.lambda_H, NaN ,  NaN, NaN,  par.AL, par.AH-par.AL,  par.sigmaK, par.eta   ];
         writetable( array2table(par_values') , target_moment_file , 'Sheet', 1,  'Range',   [ column_output{iter}, '15:',  column_output{iter}, num2str(16+length(par_values)-1) ]  ,'WriteVariableNames',false);
    else
         par_values = [   par.lambda_H, par.lambdaLH, par.lambdaHL, par.AL, par.AH-par.AL,  par.sigmaK, par.eta   ];
         writetable( array2table(par_values') , target_moment_file , 'Sheet', 1,  'Range',   [ column_output{iter}, '16:',  column_output{iter}, num2str(16+length(par_values)-1) ]  ,'WriteVariableNames',false);
    end
end


%% -------------- Simulate the General-Belief Model (Appendix) Under Different Values of theta_belief and lambda_mid --------------------------------------------------
disp('----------------------------------------------------------------------------------------------------------')
disp('--------------------- Simulated Data under General Beliefs ---------------------')
sol_behavioral =  load( ['solutions/baseline_behavioral.mat' ] );  
sol_behavioral = post_processing(sol_behavioral.model_sol);
par = sol_behavioral.par;
moments = simulation_results_output( sol_behavioral, 5000 );
avg_lambda = mean(moments.lambda_rational);   % needed for the definitions of beliefs below. 

% Plot the functional forms of each case. 
belief_fun1 = @(lambda) max( par.lambda_L + 0.001*lambda, min( par.lambda_H - 0.001*lambda,  lambda + 1.2 * sqrt( lambda - par.lambda_L ) .*  ( par.lambda_H - lambda )  )   );
belief_fun2 = @(lambda) max( par.lambda_L + 0.001*lambda, min( par.lambda_H - 0.001*lambda,   3 * ( lambda - par.lambda_L ).^3  )   );
belief_fun3 = @(lambda) max( lambda, min( par.lambda_H - 0.001*lambda,  lambda + 2.3* sqrt( lambda - par.lambda_L ) .*  ( 2*avg_lambda - lambda )  )   );
belief_fun4 = @(lambda)  (lambda>avg_lambda).*min( par.lambda_H-0.001*par.lambda_H + 0.001*lambda ,lambda + 1* ( lambda -  avg_lambda ).^(1/3) .*  ( par.lambda_H - lambda )) + (lambda<=avg_lambda).* lambda   ;
belief_fun5 = @(lambda) min(lambda, 97* ( lambda - par.lambda_L ).^4)   ;
belief_fun6 = @(lambda) min( lambda, min( par.lambda_H - 0.001*lambda,  avg_lambda + 4.5 * ( lambda - avg_lambda ).^3  )   );

N_years = 20000;
belies_list = { belief_fun1,  belief_fun2, belief_fun3, belief_fun4, belief_fun5, belief_fun6};
columns = {'B', 'C', 'D', 'E', 'F', 'G'};
for(iter = 1:length(belies_list))
    sol = sol_behavioral;
    sol.par.belief_fun = belies_list{iter};
    rng(1);  % set seed so that it is replicable.
    moments = simulation_general_belief_results_output( sol, N_years );
    simulation_key_moments_for_parameter_calibration;   % scripts that define the moments to be output, in the function "calibration_moments". 
    output_matrix = [ calibration_moments(moments, sol.par) ];
    writetable( array2table(output_matrix(1:8)') , target_moment_file_general_belief ,'Sheet', 1,  'Range',  [ [columns{iter}, num2str(2) ] , [ ':', columns{iter}, num2str(9) ] ], 'WriteVariableNames', false );  
end


%% ------------------  For Appendix B Tables: Store the General-Belief Calibrated Results in Excel. ---------------------
disp('----------------------------------------------------------------------------------------------------------')
disp('--------------------- Appendix Table 8 and 9: Calibrated Parameters and Target Moments for General Beliefs (output to file "moment_target.xlsx") ---------------------')
model_list={ 'optimistic', 'pessimistic' };    column_output = {'G','H'};
target_values =  readtable( target_moment_file, 'Sheet',1,  'Range',  ['B3:B10'] ,'ReadVariableNames',false).Variables;
simulation_key_moments_for_parameter_calibration;
for( iter = 1:length(model_list) )
    disp( ['>>>>>>> simulating the ', model_list{iter}, ' model >>>>>>>'] )
    S = load( ['solutions/baseline_', model_list{iter}, '.mat' ] );
    m = simulation_results_output(S, 15000);  % the second parameter is simulation year
    calibrated_par_values = calibration_moments(m,S.model_sol.par);
    writetable( array2table(calibrated_par_values([1:8,15:16])') , target_moment_file , 'Sheet', 2,  'Range',   [ column_output{iter}, '3:',  column_output{iter}, num2str(3+length(target_values)+1) ]  ,'WriteVariableNames',false);
    par = S.model_sol.par;
    par_values = [  par.AL, par.AH-par.AL,  par.lambda_H, par.lambdaLH, par.lambdaHL, par.sigmaK, par.eta   ];
    writetable( array2table(par_values') , target_moment_file , 'Sheet', 2,  'Range',   [ column_output{iter}, '16:',  column_output{iter}, num2str(16+length(par_values)-1) ]  ,'WriteVariableNames',false);
end



