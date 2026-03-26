###################voc TO LUMPS #######################
sm_starts = [0,0,0,23,25,25,29,29]#####the index number of sampling to corresponse to the sectors 
sm_ends = [22,22,22,24,28,28,85,85]

sectors = ['transportation','aviation','shipping','energy','agriculture','waste','residential','industry']



DF_emis = pd.DataFrame(columns = sectors)
#DF_ofps = pd.DataFrame(columns = sectors)
df = pd.read_csv('all_species_fraction.csv').set_index('SPECIE NAME')

mapping = pd.read_csv('mapping species to lumps.csv',sep = ';')
df78 = df.iloc[0:78,:]
df78['lumps'] = mapping['mapping to modelling species[2]'].values.tolist()
df_lp = df78.groupby('lumps').sum()



def emis_speciation(year, mon_agg):
    
    path_nc = '/mnt/beegfs/user/yjzhang/emission/integrated_all/'+year+mon_agg+'/Integrated_Anthropogenic_'+year+'_'+mon_agg+'_NMVOC_0.25x0.25.nc'
    emis_ds = xr.open_dataset(path_nc)
    lon_arange = emis_ds.lon.values##MEIC lat-lon ranges
    lat_arange =  emis_ds.lat.values
    for lp, lp_idx in zip(df_lp.index.values.tolist(), np.arange(0,df_lp.shape[0],1)):
        voc_emis=xr.Dataset(
            coords = {'lon': lon_arange,
                      'lat': lat_arange})
        
        for sm_start, sm_end, sec in zip(sm_starts, sm_ends,sectors):
            df_sec = df_lp.iloc[:,sm_start:sm_end]#.mean(axis = 1)
            df_sec.replace(np.nan, 0, inplace=True)
            perc_sec = df_sec.mean(axis = 1)
            emis_subsectors = np.zeros((df_sec.shape[1],200,320), dtype='float32')
            for i in np.arange(0,df_sec.columns.values.shape[0],1):
                emis_subsectors[i,:,:] = emis_ds[sec] * df_sec.iloc[lp_idx,i] * 0.01
            emis_sectors = emis_subsectors.sum(axis = 0)
            voc_emis[sec] = (('lat', 'lon'), emis_sectors)
        save_dir = '/mnt/beegfs/user/yjzhang/emission/integrated_all/'+year+mon_agg+'/' 
        output = save_dir + '/' + 'Integrated_Anthropogenic_' + year +'_'+mon_agg+'_' + lp + '_0.25x0.25' +'.nc'#####automatically the date
        voc_emis.to_netcdf(output,format="NETCDF3_CLASSIC")