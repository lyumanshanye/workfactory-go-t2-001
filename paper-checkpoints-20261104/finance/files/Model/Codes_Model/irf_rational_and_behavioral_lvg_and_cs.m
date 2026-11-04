function   imp = irf_rational_and_behavioral_lvg_and_cs(    current_model , years_simulation, leverage, cs, dN_after,  options, m_simulation )

if( nargin<=5 )
    options.random = false;
end

disp(  [  '----------------- Generating the impulse response function for a ', current_model.par.model_name, ' model --------------------'   ]  )

par = current_model.par;
% Find the correct scaling for the credit spread. 
w_dim = kron(ones(par.N_lambda,1), par.w_grid );
lambda_dim = kron(par.lambda_grid, ones(par.N_w,1));
fit_a_function = @(values_matrix)  scatteredInterpolant(w_dim,    lambda_dim ,  reshape( values_matrix, par.N_w*par.N_lambda, 1 ),   'linear')  ;
if(nargin<=6)
    m_simulation = simulation_results_output(current_model);
end
spread_fitted = fit_a_function(current_model.credit_spread/m_simulation.mean_spread_before_normalization);   % Re-adjust with the average
lvg_fitted = fit_a_function( current_model.xK_matrix );

% %  Calculate the initial state of lambda
solve_w_and_lambda_fun = @( states )  [ lvg_fitted( states(1), states(2) ) - leverage;  spread_fitted( states(1), states(2) ) - cs ] ;   % states = [w, lambda]
opt_solver = optimset('Display','on');
[ solution, e  ] = fsolve( solve_w_and_lambda_fun,   [ 0.08,   (par.lambda_L+par.lambda_H)/2 ]  , opt_solver  );
w = solution(1);
lambda_belief= max(min(solution(2),par.lambda_H), par.lambda_L);
if( lambda_belief<=par.lambda_L || lambda_belief>=par.lambda_H || sum(abs(e))>10^(-5) )
    disp(  ['Error in solving the appropriate lambda! lambda=',num2str(lambda_belief)] );
else
    disp( ['Initial w=', num2str(w)  ,',  Initial believed lambda=', num2str(lambda_belief) ]  )
end

if( strcmp( current_model.par.model_name, 'behavioral' ) )    
    lambda_underlying_fun = @(lambda_underlying)      irrational_lambda(  lambda_underlying, par.lambda_reference, par.lag_years ,  par)  - lambda_belief; 
    [ solution, ~  ] = fsolve( lambda_underlying_fun,   lambda_belief  , optimset('Display','off')  );
    lambda_underlying = solution;
else
    lambda_underlying = lambda_belief;
end

imp = irf_rational_and_behavioral_w_and_lambda( current_model , years_simulation,  w,  lambda_underlying,  dN_after,  options, m_simulation);
imp.lambda_belief = lambda_belief;


