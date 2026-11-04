function   results = post_processing( model_sol,   simplified,  export_figure, behavioral_option )
% Usage: post_processing( parameters,  model_sol )
% This function generates relevant results for a model solutiont(2D solutions with state variables (w, lambda)
if( nargin<2 )
    simplified = false;
end
if(nargin<3)
    export_figure = false;
    behavioral_option = 2;
end

%% SECTION 1. Setting PARAMETERS
par = model_sol.par;
alpha  = par.alpha ;   beta = par.beta;   
e = par.e;  varepsilon=par.varepsilon;  % Bank Run par.
eta = par.eta;  
AH = par.AH;   AL=par.AL; 
rho = par.rho;   sigmaK=par.sigmaK;  delta=par.delta;    
investment =  par.investment;      muK_fun = par.muK_fun;     
mu_lambda_fun=par.mu_lambda_fun;   kappa_lambda_fun = par.kappa_lambda_fun;
lag_years = par.lag_years;
N_w = par.N_w;    N_lambda = par.N_lambda;  
w_grid = par.w_grid;   lambda_grid=par.lambda_grid;  

muR1 = -delta + muK_fun(par.p1) - investment(par.p1)/par.p1;
xK1 = 1;
rf1 = muR1 + AH/par.p1 - (sigmaK)^2*xK1;

muR0 = -delta + muK_fun(par.p0) - par.investment(par.p0)/par.p0;
xK0 = (AH-AL)/par.p0/( sigmaK^2 ) + 1;
rf0 = muR0 + AH/par.p0 - (sigmaK)^2*xK0;


%% ********** Post processing for the rational benchmark **********
w_dim = kron(ones(N_lambda,1), w_grid );
lambda_dim = kron(lambda_grid, ones(N_w,1));
fit_a_function = @(values_matrix)  scatteredInterpolant(w_dim,    lambda_dim ,  reshape( values_matrix, N_w*N_lambda, 1 ),   'linear')  ;

% par
w_matrix = kron(  w_grid,   ones( 1, N_lambda )   );
lambda_matrix = kron(  ones( N_w, 1 ),   lambda_grid'   );

% if it is the benchmark model, then just use the average values. 
if( par.model_name=="benchmark" )
    p_matrix = mean(model_sol.p_matrix,2) * ones(1, N_lambda) ;
    kappap_matrix =  mean(model_sol.kappap_matrix,2) * ones(1, N_lambda) ;
    p_fitted = fit_a_function(p_matrix);  % the p function used by agents to form expectations.
else
    p_matrix = model_sol.p_matrix;
    kappap_matrix = model_sol.kappap_matrix;
    p_fitted = fit_a_function(p_matrix);  % the p function used by agents to form expectations.
end

% Productivity and Portfolio choices
psi_matrix = ( investment(p_matrix) + rho.*( p_matrix ) - AL ) ./ (AH-AL);   % psi constructed from price.
productivity_matrix = psi_matrix*AH + (1-psi_matrix)*AL;
xK_matrix = psi_matrix./w_matrix;   % note: this definition fails at w=0 
xK_matrix(1,:) = xK_matrix(2,:);
yK_matrix = ( 1 - w_matrix.*xK_matrix  ) ./ ( 1 - w_matrix );
yK_matrix(end,:) = yK_matrix(end-1,:);
delta_x_matrix = beta*max(xK_matrix-1,0);
indicator_matrix = delta_x_matrix>0 ;


% Jumps. Fix the non-monotone component. (minor deviations, but may cause
% large unreasonable results as the denominator goes to zero)
kappab_survival_matrix = min(xK_matrix.*kappap_matrix+alpha*delta_x_matrix, 1-20*e);
for( j = 1:5 )
    kappab_row = kappab_survival_matrix(:,j);
    for( starting_w = 0.2:0.05:0.6 )
        index = find(w_grid>=starting_w, 1, 'first');
        fitted = slmengine( w_grid(2:index) ,  kappab_row(2:index) ,'plot', 'off', 'decreasing', 'on',  'leftvalue', kappab_row(2) , 'rightvalue',  kappab_row(index) );  
        if( sum(sum(isnan(fitted.coef)))==0 )
            break;
        end
    end
    kappab_survival_matrix(1:index,j) = slmeval( w_grid(1:index),  fitted);
end

if(par.model_name=="benchmark")
    kappab_survival_matrix = kappab_survival_matrix(:,1) * ones(1, N_lambda);
end

kappap_matrix = (kappab_survival_matrix-alpha*delta_x_matrix) ./ xK_matrix;

% resolve the kappaw matrix with the new kappab survival matrix. 
kappab_matrix = min( kappab_survival_matrix, 1-20*e );
kappa_fs_matrix = alpha*delta_x_matrix.*w_matrix./(1-w_matrix);   kappa_fs_matrix(end,:) = kappa_fs_matrix(end-1,:);
kappah_matrix = varepsilon + (1-varepsilon)*yK_matrix.*kappap_matrix - kappa_fs_matrix;
kappaw_matrix_init = 1 -  (1-kappab_matrix) ./ ( (1-(1-w_matrix).*kappah_matrix-w_matrix.*kappab_matrix) ) ;
kappaw_matrix = kappaw_matrix_init;

% for( i = 2:(N_w-1) )
%     for(j=1:N_lambda)
%         kappaw_residual =  @(kappaw)  p_matrix(i,j) - p_fitted(  w_grid(i).*(1-kappaw), lambda_grid(j)+par.kappa_lambda_fun(lambda_grid(j)) ) - kappap_matrix(i,j) + 10^(10)*( kappaw > 0.99) ; 
%         [kappaw, fval ,~,~] = fzero( kappaw_residual, kappaw_matrix(i,j) );
%         kappaw_matrix(i,j) = kappaw;
%     end
% end

w_post_matrix = w_matrix.*( 1- kappaw_matrix );

% ---- Newly added on July 7, 2023. ----
lambda_post_matrix = par.kappa_lambda_fun(lambda_matrix) + lambda_matrix;
kappap_matrix = (p_matrix - p_fitted(w_post_matrix, lambda_post_matrix) ) ./ p_matrix;  

% ---- End of newly addition ----

p_post_matrix = p_matrix .* (1-kappap_matrix);

psi_post_matrix = ( investment(p_post_matrix) + rho.*( p_post_matrix ) - AL ) ./ (AH-AL); 
productivity_post_matrix = psi_post_matrix*AH + (1-psi_post_matrix)*AL;
kappa_productivity_matrix = 1 - productivity_post_matrix./productivity_matrix;
kappa_output_matrix = 1 - (1-varepsilon)*productivity_post_matrix./productivity_matrix;  % capital becomes 1-varepsilon from 1 after crises.

% % Consistency check: whether the post crises prices are consistent using two different methods
% lambda_post_matrix = lambda_matrix + kappa_lambda_fun(lambda_matrix);
% p_post_matrix_new = p_fitted( w_post_matrix, lambda_post_matrix );
% subplot(1,2,1); plot(w_grid, p_post_matrix);
% subplot(1,2,2); plot(w_grid, p_post_matrix_new)

% % Another way to calculate output change.
% w_post = w_matrix .* (1-kappaw_matrix);
% lambda_post = par.kappa_lambda_fun(lambda_matrix) + lambda_matrix;
% productivity_fun = fit_a_function(productivity_matrix);
% kappa_output_matrix_new = 1 - productivity_fun(w_post, lambda_post) ./ productivity_matrix  ;
% p_matrix_new = p_fitted( w_post, lambda_post );
% kappap_matrix_new = 1 - p_matrix_new./p_matrix;
% plot( lambda_grid, kappa_output_matrix, lambda_grid, kappa_output_matrix_new, '--' )
% plot( w_grid, kappap_matrix_new, w_grid, kappap_matrix, '--' )


% Price derivatives and volatilities
[pw_matrix,  plambda_matrix] = derivative2D(  w_grid, lambda_grid, p_matrix );
pww_matrix = zeros(size(pw_matrix));
for(  j = 1:N_lambda )
    pw_fitted = slmengine( w_grid , pw_matrix(:,j), 'plot', 'off' , 'decreasing', 'on', 'concaveup', 'on',   'knots',   floor( N_w /2)   );
    pw_matrix(:,j) = slmeval(  w_grid, pw_fitted );
    pww_matrix(:,j) =  slmeval(  w_grid, pw_fitted, 1 );
end
% [pww_matrix, ~] = derivative2D(  w_grid, lambda_grid, pw_matrix );

if( par.model_name=="benchmark" )
    plambda_matrix = 0;
end

sigmap_matrix = pw_matrix.*w_matrix.*(1-w_matrix).*(xK_matrix- yK_matrix ) ./ ( 1- pw_matrix.*w_matrix.*(1-w_matrix).*(xK_matrix - yK_matrix )  ).* sigmaK; 
sigmab_matrix = xK_matrix .* (sigmaK + sigmap_matrix );
sigmah_matrix = yK_matrix .* (sigmaK + sigmap_matrix ); 
sigmaw_matrix = (1-w_matrix).*( sigmab_matrix - sigmah_matrix );


% Growth rates and interest rates
muR_r_matrix = (sigmap_matrix+sigmaK).^2.*xK_matrix + lambda_matrix.*(kappap_matrix+alpha*beta)./( 1 -  kappab_survival_matrix ) - AH./p_matrix;
muR_r_matrix(:,end) = muR_r_matrix(:,end-1);
mu_lambda_matrix = mu_lambda_fun( lambda_matrix );
mup_matrix = pw_matrix.*w_matrix.*( 1-w_matrix ) .* (  (xK_matrix-yK_matrix).*muR_r_matrix + 1./p_matrix.*( xK_matrix*AH - yK_matrix*AL ) +  sigmah_matrix.^2 - sigmab_matrix.*sigmah_matrix - w_matrix.*(sigmab_matrix-sigmah_matrix).^2 - eta    ) ... 
    + 0.5.*pww_matrix.*(  w_matrix.*(1-w_matrix).*(sigmab_matrix-sigmah_matrix) ).^2 + plambda_matrix.*mu_lambda_matrix ;
muR_matrix = mup_matrix - delta + sigmaK*sigmap_matrix + muK_fun(p_matrix)   - investment(p_matrix)./p_matrix;
rd_matrix = muR_matrix - muR_r_matrix ;
rf_matrix = rd_matrix + lambda_matrix.*alpha*beta./( 1 -  kappab_survival_matrix );  % the interbank risk-free rate
for(j=1:N_lambda)
    rf_vec = rf_matrix(:,j); 
    rf_fitted = slmengine( w_grid, rf_vec,  'increasing', 'on');
    rf_matrix(:,j) = slmeval( w_grid,  rf_fitted  );
end

mub_matrix =  rd_matrix + xK_matrix.*(muR_r_matrix+AH./p_matrix) -  rho;
muh_matrix = rd_matrix + yK_matrix.*(muR_r_matrix+AL./p_matrix) -  rho;

muw_definition  % Source the muw definition codes to define muw_matrix.

sharpe_ratio_matrix = (muR_matrix + AH./p_matrix - lambda_matrix.*kappap_matrix - rf_matrix) ./ (   (sigmap_matrix+sigmaK).^2 + lambda_matrix.*kappap_matrix  );

% capital risk premium
capital_risk_premium = (sigmaK+sigmap_matrix).^2 .* xK_matrix + lambda_matrix.*kappap_matrix./(1-kappab_matrix) - lambda_matrix.*kappap_matrix;
equity_risk_premium = xK_matrix.*(sigmaK+sigmap_matrix).^2.*xK_matrix + (xK_matrix.*kappap_matrix+alpha*(xK_matrix-1) ) .* lambda_matrix .*kappab_matrix./(1-kappab_matrix) ;

capital_drift_matrix = (sigmaK+sigmap_matrix).^2 .* xK_matrix + lambda_matrix.*(kappap_matrix+alpha)./(1-kappab_matrix) - lambda_matrix.*alpha*beta./( 1 -  kappab_survival_matrix );   % Note: the last component adjusts for the difference betweeen rd and rf
equity_drift_matrix = xK_matrix .* capital_drift_matrix;

% Fit other functions 
xK_fun = fit_a_function(xK_matrix);
yK_fun = fit_a_function(yK_matrix);
delta_x_fun = fit_a_function(delta_x_matrix);
kappa_fs_fun = fit_a_function(kappa_fs_matrix);
kappap_fun = fit_a_function(kappap_matrix);

%% ************ Solve for the behavioral dynamics ************
% Two Step Process: (1) Use the rational belief to get a new w, and update % the price of capital as p( w, lambda^theta ).  (2) Use the difference
% between p(w, lambda^theta) and p(w, lambda) to trigger another round of decline in the price of capital. 

lambda_hat_fun = @(lambda_rational, lambda_reference)  irrational_lambda(lambda_rational, lambda_reference, lag_years, par);
w_post_fun = fit_a_function(w_post_matrix);

w_tensor_grid =  zeros( [N_w, N_lambda, N_lambda] );   
lambda_tensor_grid = zeros( [N_w, N_lambda, N_lambda] );
lambda_reference_tensor_grid = zeros( [N_w, N_lambda, N_lambda] );
kappap_tensor = zeros( [N_w, N_lambda, N_lambda] );   % note: the second dimension is the rational lambda, and the third dimension is the reference point
kappaw_tensor = zeros( [N_w, N_lambda, N_lambda] );
kappab_tensor  = zeros( [N_w, N_lambda, N_lambda] );
solved_indicator_tensor =  true( [N_w, N_lambda, N_lambda] );

if( strcmp(par.model_name,"behavioral")  )   % only execute the following if we want behavioral part

disp(  ['***Solving the equilbrium jumps with behavioral beliefs'] )
for( iter_lambda_reference = 1:N_lambda )
    lambda_reference = lambda_grid(iter_lambda_reference);
    lambda_reference_tensor_grid( :, :, iter_lambda_reference ) = lambda_reference;
%     disp( ['iteration on lambda reference: iter=', num2str(iter_lambda_reference) ] );
    for( iter_lambda = 1:N_lambda )  % Iterate over the current rational lambda. 
        lambda_rational_pre = lambda_grid(iter_lambda);   % This is the rational lambda after a crisis shock, and in the interrim period.
        lambda_rational_post = lambda_rational_pre + kappa_lambda_fun(lambda_rational_pre); 
        lambda_pre = lambda_hat_fun(lambda_rational_pre, lambda_reference);
        lambda_interrim = lambda_pre + kappa_lambda_fun(lambda_pre);
        lambda_post = lambda_hat_fun(lambda_rational_post, lambda_reference);
        w_tensor_grid( :, iter_lambda, iter_lambda_reference) = w_grid;
        lambda_tensor_grid( :, iter_lambda, iter_lambda_reference) = lambda_rational_pre;
        for( iter_w = 2:(N_w-1) )
            w_pre = w_grid(iter_w);       p_pre = p_fitted(w_pre, lambda_pre);     xK_pre=xK_fun(w_pre, lambda_pre);
                         
            % % STEP 1: USE the rational belief to get a new w, and a new p.
            w_interrim = w_post_fun(w_pre, lambda_pre);    % Important: w is the post-crisis w. 
            xK_interrim=xK_fun(w_interrim, lambda_interrim);   % note: lambda_interrim = lambda_post, because later it is not an adjustment of lambda
            p_interrim = p_fitted( w_interrim, lambda_interrim );
%             p_expected = p_fitted(w_interrim, lambda_pre + kappa_lambda_fun(lambda_pre) );

            % % STEP 2: Compare the actual price with the interrim price (expected price), and make an adjustment.
            residual_fun = @(dp)  kappa_iterative_residual_diagnostic_belief(  dp,   w_interrim,    xK_interrim,   p_interrim,   lambda_post,  p_fitted,  par ) ;
            [dp, fval ,~,~] = fzero( residual_fun, 0 );  % Important: use subscript k
            solved_indicator_tensor(iter_w, iter_lambda, iter_lambda_reference) = fval<1e-5; 
            [~,w_post] = kappa_iterative_residual_diagnostic_belief(  dp,   w_interrim,    xK_interrim,   p_interrim,   lambda_post,  p_fitted,  par );
            p_post = p_fitted(w_post, lambda_post);
%             dp_vec = linspace( -0.01, 0.01, 100 ); 
%             plot( dp_vec, residual_fun(dp_vec)  )

%             % % STEP 2: Compare the actual price with the interrim price (expected price), and make an adjustment.
%             xK_pre = xK_fun(w_pre, lambda_pre);
%             residual_fun = @(kp)  kappa_iterative_residual_diagnostic_belief( kp,   w_pre,    xK_pre,   p_pre,   lambda_post,  p_fitted,  par ) ;
% 
%             [kp, fval ,~,~] = fsolve( residual_fun, 0.001 , optimset( 'Display','none' ) );  % Important: use subscript k
%             solved_indicator_tensor(iter_w, iter_lambda, iter_lambda_reference) = fval<1e-5; 
%                [~,  w_post] = kappa_iterative_residual_diagnostic_belief(  kp,   w_pre,    xK_pre,   p_pre,   lambda_post,  p_fitted,  par ) ;
%                 p_post = p_pre *(1-kp);

%             if(fval>0.001)
%                disp('not solved');
%                kp_vec = linspace( 0, 0.002, 100 )'; 
%                residual_vec = linspace( -0.01, 0.01, 100 )'; 
%                 for(i = 1:length(kp_vec))
%                     residual_vec(i) = residual_fun( kp_vec(i) );
%                 end
%                plot( kp_vec, residual_vec  );
%                pause(10);
%             end

            kappap_tensor( iter_w, iter_lambda, iter_lambda_reference ) = (p_pre - p_post)/p_pre;
            kappaw_tensor( iter_w, iter_lambda, iter_lambda_reference ) = (w_pre-w_post) /w_pre; 
            kappab_tensor( iter_w, iter_lambda, iter_lambda_reference ) =  ( w_pre.*p_pre - w_post .* p_post ) ./ (w_pre.*p_pre); 

            % Solve for the equity and capital excess risk premium. Two sources of discrepance: (1) Actual crises
            % frequency in the behavioral belief is different from the reality.  (2) The severity of a crisis is larger
            % in the behavioral model.
        end
    end
end

if( sum(sum(sum(~solved_indicator_tensor))) > 0  )
    disp(   [ num2str(sum(sum(sum(~solved_indicator_tensor)))),   ' unsolved kappap in the behavioral case! (post_processing)'  ]   )
end
 

% plot the 3rd dimension
if(export_figure)
    for( k = 1:10  )
        figure( 'Position', [0 0 800 500] ) ;    
        subplot(1,2,1); plot( lambda_grid, reshape( -kappap_tensor(30, k, :), [], 1),  lambda_grid,  -kappap_tensor(30, k, k)*ones(size(lambda_grid)) , '-.' ,   lambda_grid(k)*ones( 2,1 ), [-0.044, 0] , '--'  );  ylim( [-0.044, 0] );
        ylabel( 'price percentage drop during a run shock' ); xlabel( 'Reference belief \lambda_{t-t0}' ); title(['\kappa^w with \lambda_t=', num2str(lambda_grid(k)) ]);
        legend( 'change with the two-step process',  'change under rational benchmark', 'current belief \lambda_t' );
        subplot(1,2,2); plot( lambda_grid, reshape( -kappaw_tensor(30, k, :), [], 1),  lambda_grid,  -kappaw_tensor(30, k, k)*ones(size(lambda_grid)) , '-.' ,   lambda_grid(k)*ones( 2,1 ), [-1, 0], '--'  );   ylim( [-1, 0] );
        ylabel( 'bank equity percentage drop during a run shock' ); xlabel( 'Reference belief \lambda_{t-t0}' );  title(['\kappa^b with \lambda_t=', num2str(lambda_grid(k)) ]);
        legend( 'change with the two-step process',  'change under rational benchmark', 'current belief \lambda_t' );
        if(behavioral_option==2)
            saveTightFigure( [  '../Figures/behavioral_belief_and_severity_of_crises/behavioral_and_crisis_',  num2str(k)  ,'.pdf' ] ); 
        else
            saveTightFigure( [  '../Figures/behavioral_belief_and_severity_of_crises/behavioral_and_crisis_one_step_',  num2str(k)  ,'.pdf' ] ); 
        end
    end
end

end  % Without no behavioral indicator

%% ********* Output *********
results = model_sol;

% % (0) Basic Boundary Values
results.rf1 = rf1;
results.rf0 = rf0;

% % (1) Dimensions
results.w_matrix = w_matrix;
results.lambda_matrix = lambda_matrix; 
results.p_fitted = p_fitted;
results.kappap_matrix = kappap_matrix;

% % (2) Quantities and prices invariant to theta (rationality), i.e. given the same state variable lambda (lambda_behavioral)
% and w, results are the same
results.xK_matrix = xK_matrix;
results.yK_matrix = yK_matrix;
results.productivity_matrix = productivity_matrix;
results.psi_matrix = psi_matrix;
results.delta_x_matrix = delta_x_matrix;
results.indicator_matrix = indicator_matrix;
results.muR_matrix = muR_matrix;
results.rd_matrix = rd_matrix;
results.rf_matrix = rf_matrix;
results.mup_matrix = mup_matrix;
results.kappad_matrix = par.varepsilon * ones(size(psi_matrix));
results.kappa_fs_matrix = kappa_fs_matrix;
results.kappaK = varepsilon;
results.muh_matrix = muh_matrix;
results.sigmah_matrix=sigmah_matrix;

results.muw_matrix = muw_matrix;
results.sigmaw_matrix = sigmaw_matrix;
results.sigmap_matrix = sigmap_matrix; 
results.mub_matrix = mub_matrix;
results.sigmab_matrix  =  sigmab_matrix;

results.muw_transition_component = muw_transition_component;

% % (3) Special to rational benchmark
results.kappaw_matrix = kappaw_matrix;
results.kappa_productivity_matrix=kappa_productivity_matrix;
results.productivity_post_matrix = productivity_post_matrix;
results.kappa_output_matrix=kappa_output_matrix;
results.kappab_survival_matrix = kappab_survival_matrix;
results.kappab_matrix = kappab_matrix;
results.sharpe_ratio_matrix = sharpe_ratio_matrix;

% % (4) Risk Premium 
results.capital_risk_premium = capital_risk_premium;
results.equity_risk_premium  = equity_risk_premium;

results.capital_drift_matrix = capital_drift_matrix;
results.equity_drift_matrix = equity_drift_matrix;

if(~simplified)
results.kappaw_fitted_matrix =  fit_a_function(kappaw_matrix); 
results.muw_fitted_matrix = fit_a_function( muw_matrix );
results.sigmaw_fitted_matrix = fit_a_function(sigmaw_matrix);
results.sigmap_fitted_matrix = fit_a_function(sigmap_matrix);
results.rd_fitted_matrix = fit_a_function(rd_matrix);
results.xK_fitted_matrix = fit_a_function(xK_matrix);
results.rf_fitted_matrix = fit_a_function(rf_matrix); 
results.kappap_fitted_matrix = fit_a_function(kappap_matrix);
results.kappab_fitted_matrix = fit_a_function(kappab_matrix);
if(isfield(model_sol,'credit_spread'))
    results.spread_raw_fitted = fit_a_function(model_sol.credit_spread);
end

% % (4) Special to behavioral model
if( strcmp(par.model_name,"behavioral") )
% construct the grids for (w, lambda_rational, lambda_reference). 
results.w_tensor_grid = w_tensor_grid; 
results.lambda_tensor_grid   = lambda_tensor_grid; 
results.lambda_reference_tensor_grid = lambda_reference_tensor_grid; 

results.kappaw_tensor = kappaw_tensor;
results.kappap_tensor = kappap_tensor;
results.kappab_tensor = kappab_tensor;

results.lambda_hat_fun=lambda_hat_fun;

lambda_reference_tensor_dim = reshape(  lambda_reference_tensor_grid(2:(N_w-1), :, :) , [], 1 );
w_tensor_dim = reshape(  w_tensor_grid(2:(N_w-1), :, :) , [], 1 );
lambda_tensor_dim = reshape(  lambda_tensor_grid(2:(N_w-1), :, :) , [], 1 );
fit_a_tensor_function = @(values_tensor)  scatteredInterpolant(w_tensor_dim,    lambda_tensor_dim ,  lambda_reference_tensor_dim, reshape( values_tensor(2:(N_w-1),:,:), [], 1 ),   'linear',   'linear')  ;   % note: linear extrapolation at the boundary
results.fit_a_tensor_function = fit_a_tensor_function;
results.kappaw_fitted_tensor =  fit_a_tensor_function(kappaw_tensor); 
results.kappap_fitted_tensor =  fit_a_tensor_function(kappap_tensor);
results.kappab_fitted_tensor =  fit_a_tensor_function(kappab_tensor); 

end

end
