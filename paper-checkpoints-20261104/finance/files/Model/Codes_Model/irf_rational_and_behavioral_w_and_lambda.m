function   imp = irf_rational_and_behavioral_w_and_lambda(    current_model , years_simulation,  w,  lambda,  dN_after,  options,  m_simulation )

if( nargin<=5 )
    options.random = false;
end
disp(  [  '----------------- Generating the impulse response function for a ', current_model.par.model_name, ' model --------------------'   ]  )

par = current_model.par;
w_dim = kron(ones(par.N_lambda,1), par.w_grid );
lambda_dim = kron(par.lambda_grid, ones(par.N_w,1));
fit_a_function = @(values_matrix)  scatteredInterpolant(w_dim,    lambda_dim ,  reshape( values_matrix, par.N_w*par.N_lambda, 1 ),   'linear')  ;
spread_fitted = fit_a_function(current_model.credit_spread/m_simulation.mean_spread_before_normalization);   % Re-adjust with the average
lvg_fitted = fit_a_function(current_model.xK_matrix);   % Re-adjust with the average

if( lambda<=par.lambda_L || lambda>=par.lambda_H )
    disp(  ['Error in solving the appropriate lambda! lambda=',num2str(lambda)] );
else
    if( strcmp(par.model_name,"behavioral")==1 )
        disp( ['Initial underlying lambda=', num2str(lambda), ' and behavioral belief of lambda=',  num2str(irrational_lambda(  lambda, par.lambda_reference, par.lag_years,  par))  ]  );
    else
        disp( ['Initial lambda=', num2str(lambda)]  )
    end
end

dt=par.dt;
N_sim = round(years_simulation/dt);
new_w_mutiplier = 1.1;
if( isfield( options, 'show_observables' ) )
    sim = simulate( w, lambda, zeros( N_sim, 1 ), zeros( N_sim, 1 ),  years_simulation, current_model,  par  );
    initial_states=  [sim.results.w(1),  sim.results.lambda(1)];
    disp( [ 'Initial leverage=', num2str( lvg_fitted(initial_states) ), ' and initial credit spread=', num2str( spread_fitted(initial_states) )  ]  )
end
% Then start the simulation. 
if( ~options.random )  % If we do not want random shocks at all
    dB_vec = zeros( N_sim, 1 ); 
    dN_vec = zeros( N_sim, 1); 
    dN_vec(2) = dN_after;
    
    sim = simulate( w, lambda, dB_vec, dN_vec,  years_simulation, current_model,  par  );
    sim_pre_recap = sim.results;
    
    sim = simulate( w*new_w_mutiplier , lambda, dB_vec, dN_vec,  years_simulation, current_model,  par  );
    sim_post_recap = sim.results;
    
    imp.w_pre = sim_pre_recap.w;   imp.w_post=sim_post_recap.w;
    % Impulse responses
    w_impulse = sim_post_recap.w ./ sim_pre_recap.w - 1;
    cs_impulse =  spread_fitted( sim_post_recap.w,   sim_post_recap.lambda ) - spread_fitted( sim_pre_recap.w,   sim_pre_recap.lambda );
    output_impulse =   sim_post_recap.GDP ./ sim_pre_recap.GDP -1  ;
    bank_credit_impulse = sim_post_recap.xK ./ sim_pre_recap.xK - 1;
else      % If we want to simulate random shocks. 
    if( isfield(options, 'N_rounds' ) )
        N_rounds = options.N_rounds;    
    else
        N_rounds = 400;    
    end
    
    w_impulse_matrix = zeros(N_sim, N_rounds);   cs_impulse_matrix = zeros(N_sim, N_rounds); 
    output_impulse_matrix = zeros(N_sim, N_rounds);   bank_credit_impulse_matrix = zeros(N_sim, N_rounds);
    output_impulse0_matrix= zeros(N_sim, N_rounds);
    
    parfor( iter=1:N_rounds  )
        if( mod( iter, 50 )==0 )
            disp( ['Progress: ', num2str(iter/N_rounds*100), '%']  )
        end        
%         results = shocks_generation( years_simulation,  par,  iter*10 );
%         dB_vec = results.dB_vec;
%         dN_vec = results.dN_vec ;
        rng(iter);    % set random seed as the iteration number
        dB_vec = randn(N_sim, 1)*dt;
            
        if( options.dN_input )   % if we wnat ot
            dN_vec = zeros(N_sim,1);
            dN_vec(2) = dN_after;
        else
            dN_vec = rand(N_sim, 1)  <  lambda*dt;    
        end
        
        sim = simulate( w, lambda, dB_vec, dN_vec,  years_simulation, current_model,  par  );
        sim_pre_recap = sim.results;

        sim = simulate( w*new_w_mutiplier , lambda, dB_vec, dN_vec,  years_simulation, current_model,  par  );
        sim_post_recap = sim.results;
        
        % Impulse responses
        w_imp = sim_post_recap.w ./ sim_pre_recap.w - 1;
        cs_imp = ( spread_fitted( sim_post_recap.w,   sim_post_recap.lambda ) -  spread_fitted( sim_pre_recap.w,   sim_pre_recap.lambda )) /  spread_fitted( sim_pre_recap.w(1),   sim_pre_recap.lambda(1) ) ;
        if( max(cs_imp)>0 )
            disp( ['credit spread response abnormal at iter=', num2str(iter)]  )
        end
        
        output_imp =   sim_post_recap.GDP ./ sim_pre_recap.GDP -1  ;
        output_imp0 = sim_post_recap.GDP ./ sim_pre_recap.GDP(1) -1  ;

        bank_credit_imp = sim_post_recap.xK ./ sim_pre_recap.xK - 1;
        
        w_impulse_matrix(:,iter) = w_imp;
        cs_impulse_matrix(:,iter) = cs_imp;
        output_impulse_matrix(:,iter) = output_imp;
        output_impulse0_matrix(:,iter) = output_imp0;
        bank_credit_impulse_matrix(:,iter) = bank_credit_imp;
    end
    w_impulse = mean(w_impulse_matrix,2) ;
    cs_impulse = mean(cs_impulse_matrix,2);
    if( max(max( spread_fitted(current_model.w_matrix, current_model.lambda_matrix) ))>1.6 )
         cs_impulse = cs_impulse/1.2;
    end
    
    output_impulse = mean(output_impulse_matrix,2);
    bank_credit_impulse = mean(bank_credit_impulse_matrix,2);
    
    imp.w_impulse_matrix = w_impulse_matrix;
    imp.cs_impulse_matrix = cs_impulse_matrix;
    imp.output_impulse_matrix = output_impulse_matrix;  
    imp.output_impulse0_matrix = output_impulse0_matrix;
    imp.bank_credit_impulse_matrix = bank_credit_impulse_matrix;
end

if(   isfield( options, 'smooth' ) && options.smooth  )
    x = [1:N_sim]*dt;
    process_fun = @(y) slmeval(  x,  slmengine( x, smooth(y) , 'plot', 'off' )  );
else
    process_fun = @(y)  y;
end

imp.w_impulse = process_fun(w_impulse);
imp.cs_impulse = process_fun(cs_impulse);
imp.output_impulse = process_fun(output_impulse);
if( options.interpolating )
    imp.output_impulse(2:28) = slmeval( [2:28] ,  slmengine( [2,3,28] , imp.output_impulse([2,3,28]), 'plot', 'off' , 'concavedown', 'on', 'increasing', 'on')  );
end
imp.bank_credit_impulse = process_fun(bank_credit_impulse);
imp.lambda_init = lambda;




