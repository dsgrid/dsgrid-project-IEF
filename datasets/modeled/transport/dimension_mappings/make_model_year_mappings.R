# many-to-many-year_mapping_to_interpolate_btwn_every_other_year
library(tidyverse)
many_to_many <- tibble(from_id = c(rep(2018, 8), rep(seq(2020, 2048, by = 2), each = 3), 2018, 2018, 2050, 2050) %>% sort(),
       to_id = c(seq(2010, 2017, 1), rep(seq(2019, 2049, by = 2), each = 2), seq(2018,2050,by=2)) %>% sort(),
       fraction = c(rep(0, 8), rep(c(1,0.5,0.5), times = (2050-2018)/2), 1))
write_csv(many_to_many, "c:/users/ayip/documents/github/dsgrid-project-StandardScenarios/dsgrid_project/datasets/sector_models/tempo/dimension_mappings/model_year_to_model_year.csv")

# for DECARB Task 6: make interpolations/extrapolations for 2024/2026/2028 from 2025/2030 data based on DECARB Task 2 results
library(tidyverse)
psgr <- read_csv("C:/Users/ayip/Downloads/decarb2/passenger_energy_decarb_0923_utf8.csv")
frgt <- read_csv("C:/Users/ayip/Downloads/decarb2/freight_energy_decarb_0923_utf8.csv")

(decarb2_high_ev_load <- psgr %>%
  filter(Year %in% c(2024,2025,2026,2028,2030,2050),
         Scenario == "High",
         str_detect(Fuel, "Electricity")) %>%
  bind_rows(frgt %>%
  filter(Year %in% c(2024,2025,2026,2028,2030,2050),
         Scenario == "High",
         str_detect(Fuel, "Electricity"))) %>%
  group_by(Year) %>%
  summarize(TWh = sum(Quads)*293.0711))

my_to_my <- tibble(from_id = c(2025,2025,2030,2025,2030,2030,2035,2040,2045,2050),
       to_id =   c(2024,2026,2026,2028,2028,2030,2035,2040,2045,2050),
       from_fraction =c(decarb2_high_ev_load$TWh[decarb2_high_ev_load$Year==2024]/decarb2_high_ev_load$TWh[decarb2_high_ev_load$Year==2025],
                   decarb2_high_ev_load$TWh[decarb2_high_ev_load$Year==2026]/decarb2_high_ev_load$TWh[decarb2_high_ev_load$Year==2025] * 0.8, #.5
                   decarb2_high_ev_load$TWh[decarb2_high_ev_load$Year==2026]/decarb2_high_ev_load$TWh[decarb2_high_ev_load$Year==2030] * 0.2, #.5
                   decarb2_high_ev_load$TWh[decarb2_high_ev_load$Year==2028]/decarb2_high_ev_load$TWh[decarb2_high_ev_load$Year==2025] * 0.4, #.5
                   decarb2_high_ev_load$TWh[decarb2_high_ev_load$Year==2028]/decarb2_high_ev_load$TWh[decarb2_high_ev_load$Year==2030] * 0.6, #.5
                   1,1,1,1,1))

write_csv(my_to_my, "c:/users/ayip/documents/github/dsgrid-project-DECARB/datasets/modeled/transport/dimension_mappings/model_year_to_model_year.csv")


# make counties dimensions and mapping
library(tidyverse)
counties <- read_csv("c:/users/ayip/OneDrive - NREL (1)/counties.csv", col_types = "c")

project_counties <- read_csv("C:/Users/ayip/Documents/GitHub/dsgrid-project-DECARB/project/dimensions/counties.csv")

county_to_county <- counties %>% rename(from_id = geography) %>%
  full_join(project_counties, by = c("from_id" = "id"), keep = TRUE) %>%
  rename(to_id = id) %>%
  mutate(to_id = if_else(is.na(state), "", to_id)) %>% #  %in% c("AK","HI")
  select(-time_zone, -name, -state) %>%
  filter(!is.na(from_id)) %>%
  add_row(from_id = "46102", to_id = "46102") %>%
  arrange(from_id)

NA_either <- county_to_county %>% filter(is.na(from_id) | is.na(to_id) | from_id == "46113" | to_id == "46113")
NA_either

county_to_county %>%
  write_csv("C:/Users/ayip/Documents/GitHub/dsgrid-project-DECARB/datasets/modeled/transport/dimension_mappings/county_to_county.csv")

counties %>%
  rename(id = geography) %>%
  left_join(project_counties, by = "id") %>%
  select(id, name, state) %>%
  add_row(id = "46102", name = "Oglala Lakota", state = "SD") %>%
  arrange(id) %>%
  write_csv("C:/Users/ayip/Documents/GitHub/dsgrid-project-DECARB/datasets/modeled/transport/dimensions/counties.csv")

# 15005 kalawao also missing (not in L48)



# make other dimensions
my <- tibble(id = c(2025,2030,2035,2040,2045,2050))
write_csv(my, "c:/users/ayip/documents/github/dsgrid-project-DECARB/datasets/modeled/transport/dimensions/years.csv")

scenarios <- tibble(id = c("High+unmanaged_immediate","High+unmanaged_smooth"))
write_csv(scenarios, "c:/users/ayip/documents/github/dsgrid-project-DECARB/datasets/modeled/transport/dimensions/scenarios.csv")

subsectors <- tibble(id = "bev")
write_csv(subsectors, "c:/users/ayip/documents/github/dsgrid-project-DECARB/datasets/modeled/transport/dimensions/subsectors.csv")


subsector <- tibble(id = c(
    "Bus+N/A+BEV_200",
    "Personal_LDV+Compact+BEV_200",
    "Personal_LDV+Compact+BEV_300",
    "Personal_LDV+Compact+BEV_400",
    "Personal_LDV+Compact+PHEV_25",
    "Personal_LDV+Compact+PHEV_50",
    "Personal_LDV+Midsize+BEV_200",
    "Personal_LDV+Midsize+BEV_300",
    "Personal_LDV+Midsize+BEV_400",
    "Personal_LDV+Midsize+PHEV_25",
    "Personal_LDV+Midsize+PHEV_50",
    "Personal_LDV+Pickup+BEV_200",
    "Personal_LDV+Pickup+BEV_300",
    "Personal_LDV+Pickup+BEV_400",
    "Personal_LDV+Pickup+PHEV_25",
    "Personal_LDV+Pickup+PHEV_50",
    "Personal_LDV+SUV+BEV_200",
    "Personal_LDV+SUV+BEV_300",
    "Personal_LDV+SUV+BEV_400",
    "Personal_LDV+SUV+PHEV_25",
    "Personal_LDV+SUV+PHEV_50",
    "Truck_Heavy+Local+BEV_150",
    "Truck_Heavy+Local+BEV_300",
    "Truck_Heavy+Long-haul+BEV_300",
    "Truck_Heavy+Long-haul+BEV_500",
    "Truck_Heavy+Regional+BEV_150",
    "Truck_Heavy+Regional+BEV_300",
    "Truck_Heavy_Vocational+Local+BEV_150",
    "Truck_Heavy_Vocational+Local+BEV_300",
    "Truck_Heavy_Vocational+Regional+BEV_150",
    "Truck_Heavy_Vocational+Regional+BEV_300",
    "Truck_Light+Local+BEV_150",
    "Truck_Light+Local+BEV_300",
    "Truck_Light+Long-haul+BEV_300",
    "Truck_Light+Long-haul+BEV_500",
    "Truck_Light+Regional+BEV_150",
    "Truck_Light+Regional+BEV_300",
    "Truck_Light_Vocational+Local+BEV_150",
    "Truck_Light_Vocational+Local+BEV_300",
    "Truck_Light_Vocational+Regional+BEV_150",
    "Truck_Light_Vocational+Regional+BEV_300",
    "Truck_Medium+Local+BEV_150",
    "Truck_Medium+Local+BEV_300",
    "Truck_Medium+Long-haul+BEV_300",
    "Truck_Medium+Long-haul+BEV_500",
    "Truck_Medium+Regional+BEV_150",
    "Truck_Medium+Regional+BEV_300",
    "Truck_Medium_Vocational+Local+BEV_150",
    "Truck_Medium_Vocational+Local+BEV_300",
    "Truck_Medium_Vocational+Regional+BEV_150",
    "Truck_Medium_Vocational+Regional+BEV_300",
    "Transit_Rail"
  )) %>% mutate(name = id)

write_csv(subsector, "c:/users/ayip/documents/github/dsgrid-project-DECARB/datasets/modeled/transport/dimensions/subsectors.csv")

list_of_to_id =
  c("bev_compact","bev_midsize","bev_pickup","bev_suv",
    "phev_compact","phev_midsize","phev_pickup","phev_suv",
    "bev_light_medium_truck","bev_medium_truck","bev_non_freight_truck","bev_heavy_freight_truck",
    "bev_bus","rail_transit")

subsector_to_subsector <- subsector %>% rename(from_id = id) %>% select(-name) %>%
  mutate(to_id = list_of_to_id[c(13,1,1,1,5,5,2,2,2,6,6,3,3,3,7,7,4,4,4,8,8,12,12,12,12,12,12,11,11,11,11,9,9,9,9,9,9,11,11,11,11,10,10,10,10,10,10,11,11,11,11,14)])

subsector_to_subsector

write_csv(subsector_to_subsector, "c:/users/ayip/documents/github/dsgrid-project-DECARB/datasets/modeled/transport/dimension_mappings/subsector_to_subsector.csv")


# fix enduses
project_enduses <- read_csv("C:/Users/ayip/Documents/GitHub/dsgrid-project-DECARB/project/dimensions/enduses.csv")
evenduses_fixed <- project_enduses %>% filter(str_detect(id, "electricity_ev_") | str_detect(id, "electricity_rail_")) %>% mutate(name = id %>% str_remove_all("electricity_"), fuel_id = "electricity", unit = "kWh")
project_enduses %>% filter(!str_detect(id, "electricity_ev_")) %>% bind_rows(evenduses_fixed) %>%
  write_csv("C:/Users/ayip/Documents/GitHub/dsgrid-project-DECARB/project/dimensions/enduses.csv")

# dataset enduses
project_enduses %>% filter(str_detect(id, "electricity_ev_")) %>% write_csv("c:/users/ayip/documents/github/dsgrid-project-DECARB/datasets/modeled/transport/dimensions/enduses.csv")
