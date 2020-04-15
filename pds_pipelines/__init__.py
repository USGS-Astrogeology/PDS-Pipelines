import warnings
available_modules = {}

try:
    from pysis import isis
    available_modules['isis'] = isis
except Exception as e:
    warnings.warn('Unable to add isis to the available modules. ' +
                 f'Failed with the following {e}.')

try:
    import gdal
    available_modules['gdal'] = gdal
except Exception as e:
    warnings.warn('Unable to add gdal to the available modules. ' +
                 f'Failed with the following {e}.')
