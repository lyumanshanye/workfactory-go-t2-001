function   results = solve_for_states_from_cs_and_lvg(    current_model ,  leverage, cs,  m_simulation )

disp(  [  '----------------- Solving the initial states for the ', current_model.par.model_name, ' model --------------------'   ]  )

if(nargin<4)
    m_simulation =  simulation_results_output(current_model);
end

par = current_model.par;
% Find the correct scaling for the credit spread. 
w_dim = kron(ones(par.N_lambda,1), par.w_grid );
lambda_dim = kron(par.lambda_grid, ones(par.N_w,1));
fit_a_function = @(values_matrix)  scatteredInterpolant(w_dim,    lambda_dim ,  reshape( values_matrix, par.N_w*par.N_lambda, 1 ),   'linear')  ;
spread_fitted = fit_a_function(current_model.credit_spread);
avg_spread_before_normalization = mean( spread_fitted(m_simulation.w,m_simulation.lambda) ) ;
spread_fitted = fit_a_function(current_model.credit_spread/avg_spread_before_normalization);   % Re-adjust with the average
lvg_fitted = fit_a_function( current_model.xK_matrix );

solve_w_and_lambda_fun = @( states )  [ lvg_fitted( states(1), states(2) ) - leverage;  spread_fitted( states(1), states(2) ) - cs ] ;   % states = [w, lambda]
opt_solver = optimset('Display','on');
[ solution, e  ] = fsolve( solve_w_and_lambda_fun,   [ 0.08,   (par.lambda_L+par.lambda_H)/2 ]  , opt_solver  );
w = solution(1);     results.w=w;
lambda = solution(2);         % This is the "believed" lambda. 

lambda= max(min(lambda,par.lambda_H), par.lambda_L);
if( lambda<=par.lambda_L || lambda>=par.lambda_H || sum(abs(e))>10^(-5) )
    disp(  ['Error in solving the appropriate lambda! lambda=',num2str(lambda)] );
else
    disp( ['Initial w=', num2str(w)  ,',  Initial lambda=', num2str(lambda) ]  )
end

if(  strcmp(par.model_name, 'behavioral' )  )   
    % Solve for the current rational lambda for the behavioral model
    lambda_believed = lambda;
    residual_underlying_lambda = @(lambda_underlying)  irrational_lambda(  lambda_underlying,  par.lambda_reference, par.lag_years,  par) - lambda_believed;
    opt_solver = optimset('Display','off');
    [ solution, ~ ] = fsolve( residual_underlying_lambda,   lambda_believed  , opt_solver  );
    lambda_underlying = solution(1);
    results.lambda = lambda_underlying;
    results.lambda_reference =  par.lambda_reference;
    results.lambda_believed = lambda;
    disp( ['Underlying lambda for behavioral belief is ', num2str(lambda_underlying) ]  )
else
    results.lambda = lambda;
end









