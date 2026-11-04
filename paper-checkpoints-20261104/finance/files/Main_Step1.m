%% Codes for the article "Beliefs and Financial Crises", by Arvind Krishnamurthy and Wenhao Li.
% This is the master file that calls all other files. 
%% Set Path and Add Path
clear all;
mainpath = [fileparts(mfilename('fullpath')), '/Model'];
addpath(genpath([ mainpath, '/Codes_Model' ] ))
cd(mainpath); cd('../Tables/');
table_path = cd();   % To output tables. 
cd(mainpath); cd('../Figures/');
figure_path = cd();
cd(mainpath);

faster_run = true;   % If true, codes below will skip the calibration and generation of simulated data.

%% Calibration and Generation of Simulated Data.  This section will take a couple of datas to finish. 
if(~faster_run)
    run("run_calibration.m");   % This one takes days to run. To redo the whole calibration, you need to clean the existing content of excel files in the "calibration files" folder. Also need to remove existing solutions in subfolders of the "solutions" folder.
    run("generate_simulation_results_to_excel.m");  % This one takes about half an hour. 
end

tic
%% Generate Calibration Tables.  Table 1, 2, and appendix tables on general-belief calibration.
run("tables_calibration.m");

%% Generate Figures 
run("figures_generation.m");
close all; 

%% Generate Appendix Figures
run("Appendix_figures_generation.m");
close all; 
toc