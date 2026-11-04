function  sim = simulate( w_init, lambda_init, dB_vec, dN_vec,  N_years, model_sol,  par  )
% Usage: impulse_response_new( w, lambda, dB, dN,  eta_adjustment,  N_years, model_sol,  par  )
% dB and dN should be of the same length.
% Notes: (w, lambda) is the starting state to calculate the impulse response.
% dB_vec and dN_vec store the shocks along different periods. They can be of different length. 
% All other parameters are stored in par, including the simulation time interval dt. 
%  w_init=0.1; lambda_init=0.1; dB_vec=zeros(1200, 1 ); dN_vec=zeros(1200, 1 );  N_years=100;, model_sol=model_sol_new; par=model_sol_new.par;

if( par.print_level>0 )
    disp( '->-> Simulate the Model ->->' );
end
if(isfield(par,'scenario'))
     disp(  ['Simulating general belief: ', par.scenario, ' belief'] )
end

%% Parameters
N_w = par.N_w;    N_lambda = par.N_lambda; 
w_grid = par.w_grid;   lambda_grid=par.lambda_grid;  
w_matrix = par.w_matrix;  
delta = par.delta;  sigmaK=par.sigmaK;
dt = par.dt;     % simulate the model at dt year interval.
w_lower =  10^(-3);   % to avoid simulation error.
w_upper = 1-10^(-3);

N_sim = round(N_years/dt);
T_vec = linspace( 1, N_sim, N_sim )'*dt; 

w_dim = kron(ones(N_lambda,1), w_grid(2:(N_w-1)) );
lambda_dim = kron(lambda_grid, ones(N_w-2,1));
fit_a_function = @(values_matrix)  scatteredInterpolant(w_dim,    lambda_dim ,  reshape( values_matrix(2:(N_w-1),:) , (N_w-2)*N_lambda, 1 ),   'linear',   'linear')  ;   % note: linear extrapolation at the boundary

if( isfield(par, 'eta_adjustment') )  % adjustment for the eta parameter during simulations.
    eta_adjustment = par.eta_adjustment;
else
    eta_adjustment = 0;
end
if( isfield(par, 'lag_years') )   % the number of years for 
    lag_years = par.lag_years;
else
    lag_years = 0;
end
if( ~isfield(par, 'theta_diagnostic') )
    par.theta_diagnostic = 0;
end

% process shocks
dB_vec = dB_vec(:);   dN_vec=dN_vec(:);   % translate into column vectors
dB_vec  =  [ dB_vec; zeros( N_sim-length(dB_vec), 1 ) ];
dN_vec =  [ dN_vec; zeros(N_sim-length(dN_vec), 1 ) ];

% Evolution of lambda
mu_lambda_fun = par.mu_lambda_fun; 
kappa_lambda_fun = par.kappa_lambda_fun;

% Evolution functions for state variable w
muw_matrix_adjusted = model_sol.muw_matrix - eta_adjustment*w_matrix ;   % Additional adjustment for growth of muw
muw_fun =  fit_a_function( muw_matrix_adjusted);
sigmaw_fun =  fit_a_function(model_sol.sigmaw_matrix);
kappaw_fun =  fit_a_function(model_sol.kappaw_matrix);

% Evolution of capital K
muK_fun = par.muK_fun;  % Note: muK_fun is a function of price, so we need to fit a price function. To calculate the total drift, we need to add the depreciation on capital as well.
price_fun = fit_a_function(model_sol.p_matrix);
kappaK = model_sol.kappaK;

% Evolution of bank equity w
mub_fun =  fit_a_function( model_sol.mub_matrix );
sigmab_fun = fit_a_function( model_sol.sigmab_matrix );
kappab_fun = fit_a_function( model_sol.kappab_matrix );

%% Rational Evolutions With shocks
K_init = 1;   % Initial capital is normalized to 1
wb_init = 1;  % Initial bank equity normalized to 1. Bank equity measures the amount of equity for a bank that has never transited into households for the whole periods. 
rational_evolution = zeros( N_sim, 4  );   % Evolution after getting dB_or_dN shocks
rational_evolution(1, :) = [ w_init, lambda_init, K_init, wb_init ] ;

% Note: use log scale to avoid explosion. 
for(  t = 1:(N_sim-1)  )
    w = rational_evolution(t,1);
    lambda_rational = rational_evolution(t,2);
    K_log = rational_evolution(t,3);
    muK = muK_fun(price_fun( w, lambda_rational) );
    wb = rational_evolution(t,4);
    rational_evolution(t+1, 1) = min( max( w .* (1 + muw_fun(w, lambda_rational)*dt + sigmaw_fun(w, lambda_rational )*dB_vec(t) - kappaw_fun(w,lambda_rational)*dN_vec(t) ),   w_lower ),  w_upper ); 
    rational_evolution(t+1, 2) = lambda_rational + mu_lambda_fun(lambda_rational)*dt + kappa_lambda_fun(lambda_rational)*dN_vec(t) ;
    rational_evolution(t+1,3) =  K_log +  ( muK - delta ) * dt  + sigmaK*dB_vec(t) - kappaK*dN_vec(t)  ;   % Note: this is in the log scale. 
    rational_evolution(t+1,4) =  max( wb * ( 1 + mub_fun(w,lambda_rational) * dt + sigmab_fun(w,lambda_rational) * dB_vec(t) -  kappab_fun(w,lambda_rational)*dN_vec(t) ),  w_lower);
end
logK_vec_original = rational_evolution(:,3);   % value before detrending
K_vec_log_detrended = rational_evolution(:,3) - linspace( rational_evolution(1,3), rational_evolution(end,3), size(rational_evolution,1)  )';
rational_evolution(:,3) = exp(K_vec_log_detrended);
% fit_fun1 = fit_a_function(model_sol.capital_risk_premium);
% capital_risk_premium_vec = fit_fun1( rational_evolution(:,1), rational_evolution(:,2) );
% fit_fun2 = fit_a_function(model_sol.equity_risk_premium);
% equity_risk_premium_vec = fit_fun2( rational_evolution(:,1), rational_evolution(:,2) );

% Find the dynamics of capital and bank equity. 
capital_drift_fun = fit_a_function(model_sol.capital_drift_matrix); 
equity_drift_fun = fit_a_function(model_sol.equity_drift_matrix); 
capital_dB_fun = fit_a_function(model_sol.sigmap_matrix+par.sigmaK); 
equity_dB_fun = fit_a_function( (model_sol.sigmap_matrix+par.sigmaK).*model_sol.xK_matrix ); 
capital_dN_fun = fit_a_function(model_sol.kappap_matrix); 
equity_dN_fun = fit_a_function(model_sol.kappab_matrix); 

w = rational_evolution(:, 1);
lambda = rational_evolution(:, 2);
capital_premium_dt_dB_dN = capital_drift_fun(w,lambda)*dt + capital_dB_fun(w,lambda).*dB_vec - capital_dN_fun(w,lambda).*dN_vec;
equity_premium_dt_dB_dN = equity_drift_fun(w,lambda)*dt + equity_dB_fun(w,lambda).*dB_vec - equity_dN_fun(w,lambda).*dN_vec;


%% Behavioral Evolutions With shocks
if( par.model_name=="behavioral" )   % if it is a behavioral model

kappaw_fitted_tensor = model_sol.kappaw_fitted_tensor;
kappap_fitted_tensor =  model_sol.kappap_fitted_tensor;
% initialize the behavioral belief.
if( isfield( par, 'lambda_reference' ) )
    lambda_reference = par.lambda_reference;
else
    lambda_reference = lambda_init;
end
lambda_behavioral_init = irrational_lambda(  lambda_init,  lambda_reference, lag_years, par  );
behavioral_evolution = zeros( N_sim, 4  );   % Evolution after getting dB_or_dN shocks
behavioral_evolution(1, :) = [ w_init, lambda_behavioral_init, K_init, wb_init ] ;
rational_lambda_vec = lambda_init * ones( N_sim, 1  );
for(  t = 1:(N_sim-1)  )
    w = behavioral_evolution(t,1);
    lambda_rational = rational_lambda_vec(t);
    lambda_behavioral = behavioral_evolution(t,2);
    periods = round(lag_years/dt);
    if(t>periods)
        lambda_reference = rational_lambda_vec( max(t-periods,1) );
    end
    K_log = behavioral_evolution(t,3);
    wb = behavioral_evolution(t,4);   %Note: this one is not as useful, since we already have the w dynamics.
    
    % update w
    muK = muK_fun(price_fun( w, lambda_behavioral) );
    kappaw = kappaw_fitted_tensor( w, lambda_rational, lambda_reference );
%     kappaw = kappaw_fun(w,lambda_rational);
    behavioral_evolution(t+1, 1) = min( max( w .* (1 + muw_fun(w, lambda_behavioral)*dt + sigmaw_fun(w, lambda_behavioral )*dB_vec(t) - kappaw*dN_vec(t) ) , w_lower ),  w_upper ); 
    
    % update rational and behavioral lambda
    lambda_current_rational = lambda_rational + mu_lambda_fun(lambda_rational)*dt + kappa_lambda_fun(lambda_rational)*dN_vec(t) ;   % the rational lambda for t+1
    rational_lambda_vec(t+1) =  lambda_current_rational;  % assign value
    if(isfield(par,'scenario'))
        % lambda_reference = (par.lambda_H * par.lambdaLH + par.lambda_L*par.lambdaHL)/(par.lambdaHL+par.lambdaLH);
        lambda_reference = 0.087; % this is the average true lambda in the baseline Bayesian calibration. 
        % overoptimistic v.s. overpessimistic
        if(strcmpi(par.scenario,'optimistic'))
            behavioral_evolution(t+1, 2) =  min( irrational_lambda(  lambda_current_rational,  lambda_reference, lag_years, par  ),  lambda_current_rational ) ;
        else   % otherwise it is a pessmistic belief. 
            behavioral_evolution(t+1, 2) =  max( irrational_lambda(  lambda_current_rational,  lambda_reference, lag_years, par  ),  lambda_current_rational ) ;
        end
    else
        % diagnostic belief
        behavioral_evolution(t+1, 2) = irrational_lambda(  lambda_current_rational,  lambda_reference, lag_years, par  );
    end
    
    % update K
    behavioral_evolution(t+1,3) =  K_log +   ( muK - delta ) * dt  + sigmaK*dB_vec(t) - kappaK*dN_vec(t)  ;
    
    % update wb
    kappab = kappap_fitted_tensor( w, lambda_rational, lambda_reference );
    behavioral_evolution(t+1,4) =  wb * ( 1 + mub_fun(w,lambda_behavioral) * dt + sigmab_fun(w,lambda_behavioral) * dB_vec(t) -  kappab*dN_vec(t) ) ;
end

logK_vec_behavioral_original =  behavioral_evolution(:,3) ;
K_vec_log_detrended = behavioral_evolution(:,3) - linspace( behavioral_evolution(1,3), behavioral_evolution(end,3), size(behavioral_evolution,1)  )';
behavioral_evolution(:,3) = exp(K_vec_log_detrended);
% capital_risk_premium_vec = model_sol.capital_risk_premium_fitted_tensor(  behavioral_evolution(:,1),  rational_lambda_vec,   [  mean(rational_lambda_vec)*ones(periods,1); rational_lambda_vec(1:(end-periods)) ]   );
% equity_risk_premium_vec = model_sol.equity_risk_premium_fitted_tensor(  behavioral_evolution(:,1),  rational_lambda_vec,   [  mean(rational_lambda_vec)*ones(periods,1); rational_lambda_vec(1:(end-periods)) ]   );


w = behavioral_evolution(:, 1);
lambda = behavioral_evolution(:, 2);
lambda_ref = [  rational_lambda_vec(1:periods);  rational_lambda_vec( 1:end-periods ) ];
kappap_vec = model_sol.kappap_fitted_tensor(w,rational_lambda_vec,lambda_ref);
xK_vec = model_sol.xK_fitted_matrix(w,lambda) ;
kappawb_vec = kappap_vec.*xK_vec + par.alpha*(xK_vec-1);
capital_premium_dt_dB_dN = capital_drift_fun(w,lambda)*dt + capital_dB_fun(w,lambda).*dB_vec - (par.alpha+kappap_vec).*dN_vec;
equity_premium_dt_dB_dN = equity_drift_fun(w,lambda)*dt + equity_dB_fun(w,lambda).*dB_vec - kappawb_vec.*dN_vec;

end




%% Store Results
sim.T_vec = T_vec;
sim.N_sim = N_sim;
sim.dB_vec = dB_vec;
sim.dN_vec = dN_vec;

sim.rational = simulation_other_outputs( rational_evolution, model_sol, par);
sim.rational.capital_risk_premium_vec = capital_premium_dt_dB_dN;
sim.rational.equity_risk_premium_vec = equity_premium_dt_dB_dN;
sim.rational.lambda_rational = rational_evolution(:,2);
sim.rational.logK_vec_original = logK_vec_original;  % This is the original K_vec without detrending.
if( par.model_name=="behavioral" )  % if it is the behavioral model, then store the behavioral results.
    sim.behavioral = simulation_other_outputs( behavioral_evolution, model_sol, par);
    sim.behavioral.capital_risk_premium_vec = capital_premium_dt_dB_dN;
    sim.behavioral.equity_risk_premium_vec = equity_premium_dt_dB_dN;
    sim.behavioral.lambda_rational = rational_lambda_vec;
    sim.behavioral.logK_vec_original = logK_vec_behavioral_original; % This is the original K_vec without detrending
end

% Store to the same field name regardless of rational or behavioral
if( par.model_name~="behavioral"  )
    sim.results = sim.rational;
else
    sim.results = sim.behavioral;
end

