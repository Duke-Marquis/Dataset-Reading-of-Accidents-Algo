crash_date = ''
crash_time = ''
borough = ''
zip_code = ''
latitude = ''
longitude = ''
location = ''
on_street_name = ''
off_street_name = ''
cross_street_name = ''
number_of_persons_injured = ''
number_of_persons_killed = ''
number_of_pedestrians_injured = ''
number_of_pedestrians_killed = ''
number_of_cyclist_injured = ''
number_of_cyclist_killed = ''
number_of_motorist_injured = ''
number_of_motorist_killed = ''
contributing_factor_vehicle_1 = ''
contributing_factor_vehicle_2 = ''
contributing_factor_vehicle_3 = ''
contributing_factor_vehicle_4 = ''
contributing_factor_vehicle_5 = ''
collision_id = ''
vehicle_type_code1 = ''
vehicle_type_code2 = ''
vehicle_type_code3 = ''
vehicle_type_code4 = ''
vehicle_type_code5 = ''

def to_csv():
    return f'{crash_date},{crash_time},{borough},{zip_code},{latitude},{longitude},{location},' \
            f'{on_street_name},{off_street_name},{cross_street_name},' \
            f'{number_of_persons_injured},{number_of_persons_killed},' \
            f'{number_of_pedestrians_injured},{number_of_pedestrians_killed},' \
            f'{number_of_cyclist_injured},{number_of_cyclist_killed},' \
            f'{number_of_motorist_injured},{number_of_motorist_killed},' \
            f'{contributing_factor_vehicle_1},{contributing_factor_vehicle_2},' \
            f'{contributing_factor_vehicle_3},{contributing_factor_vehicle_4},' \
            f'{contributing_factor_vehicle_5},{collision_id},' \
            f'{vehicle_type_code1},{vehicle_type_code2},' \
            f'{vehicle_type_code3},{vehicle_type_code4},' \
            f'{vehicle_type_code5}'   