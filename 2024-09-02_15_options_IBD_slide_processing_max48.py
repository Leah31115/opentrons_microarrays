#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug 27 15:19:08 2024

@author: Leah
"""

from opentrons import protocol_api

from math import ceil


metadata = {
    'apiLevel': '2.19',
    'protocolName': '15 options - Microarray Slide processing protocol (max 48 samples)',
    'description': 'This protocol processes IBD microarray printed slides',
    'author': 'Leah Ellis and Leo Rudczenko'
}

def run(protocol: protocol_api.ProtocolContext):
    sample_counter = protocol.params.sample_count

    # Load in pipette and tips
    tip_racks_1000 = protocol.load_labware(
        load_name="Opentrons_96_tiprack_1000ul",
        location="A1"
    )
    
    pipette_1000 = protocol.load_instrument(
        "p1000_single_gen2",
        "left",
        tip_racks=[tip_racks_1000]
    )

    # Load in volume-holding labware
    PBST_reservoir = protocol.load_labware(
        load_name="agilent_1_reservoir_290ml",
        location="B2"
    )

    water_reservoir = protocol.load_labware(
        load_name="agilent_1_reservoir_290ml",
        location="B3"
    )

    # Reagent holder for I-block, anti-IgG, and dye
    reagent_reservoir=protocol.load_labware(
        load_name="vwr_12_reservoir_20000ul",
        location="C1"
    )

    # Reagent reservoir liquid definitions
    iblock = protocol.define_liquid(
        name="I-Block",
        description="0.02% I-Block+0.05% sodium azide",
        display_color="#FFB000"
    )

    antiIgG = protocol.define_liquid(
        name="biotinylated anti-IgG",
        description="biotinylated anti-IgG human produced in goat 1:5000",
        display_color="#FF0000"
    )

    dye = protocol.define_liquid(
        name="IR800 Streptavidin Dye",
        description="IR800 Streptavidin Dye 1:1000",
        display_color="#FFA000"
    )
    # Loading the right volume of liquids into the reagent reservoir depending on sample_counter (number of samples)
    # Multiply by 1.1 to ensure the pipette aspirates the required volume without drawing in air at the bottom
    reagent_reservoir["A1"].load_liquid(
        liquid=iblock, volume=240 * sample_counter * 1.1
    )

    reagent_reservoir["A2"].load_liquid(
        liquid=antiIgG, volume=240 * sample_counter * 1.1
    )

    reagent_reservoir["A3"].load_liquid(
        liquid=dye, volume=240 * sample_counter * 1.1
    )
    
    # Load in slide holders
    slide_holder_count = ceil(sample_counter/12)
    slide_holder_slots = ["C2", "C3", "D1", "D2"]
    slide_holders = [
        protocol.load_labware(
            load_name="tighe_12_wellplate_20000ul",
            location=slideslot
        )
        for slideslot in slide_holder_slots[:slide_holder_count]
    ]

    # Load in sample plate
    sample_plate = protocol.load_labware(
        load_name="abgene_96_wellplate_300ul",
        location="D3"
    )

    # Get all wells dynamically
    # 2D list made into 1D list for sample plate rows (2D) -> sample plate columns (1D)
    available_well_numbers = [
        well
        for row in sample_plate.rows()
        for well in row
    ]
    used_wells = available_well_numbers[:sample_counter]

    # Get all slide slots across all slide holders
    # 3D list made into 1D list for slide holders (3D) -> slide holder rows (2D) -> slide holder columns (1D)
    all_slide_slots = [
        slide_slot
        for slide_holder in slide_holders
        for slide_holder_row in slide_holder.rows()
        for slide_slot in slide_holder_row
    ]
    required_slide_slots = all_slide_slots[:sample_counter]


    # Protocol steps
    # PBST wash
    def PBST_wash_single():
        for slide_slot in required_slide_slots:
            pipette_1000.distribute(240, PBST_reservoir["A1"].bottom(), slide_slot, new_tip="never", disposal_volume=0)
        protocol.delay(seconds=20)


    def PBST_washes():
        pipette_1000.pick_up_tip()
        for _ in range(4):
            PBST_wash_single()
        pipette_1000.drop_tip()


    PBST_washes()

    # I-block step
    pipette_1000.pick_up_tip()
    for slide_slot in required_slide_slots:
        pipette_1000.distribute(240, reagent_reservoir["A1"].bottom(), slide_slot, new_tip="never", disposal_volume=0)
    pipette_1000.drop_tip()

    # Incubate 1-hour with I-block
    for minute_count in range(60, 0, -1):
        protocol.delay(minutes=1, msg=f"Incubating with I-block for 60 minutes - there are {minute_count} minutes left!")

    # PBST wash
    PBST_washes()

    # Both the list of used_wells and required_slide_slots have a length equal to the sample_counter
    for well, slide_slot in zip(used_wells, required_slide_slots):
        pipette_1000.transfer(240, well, slide_slot, disposal_volume=0, new_tip="always")


    # Serum incubation
    for minute_count in range(60, 0, -1):
        protocol.delay(minutes=1, msg=f"Incubating with serum for 60 minutes - there are {minute_count} minutes left!")
    
    # PBST wash
    PBST_washes()

    # anti-IgG addition
    pipette_1000.pick_up_tip()
    pipette_1000.mix(4, 700, reagent_reservoir["A2"])
    for slide_slot in required_slide_slots:
        pipette_1000.distribute(240, reagent_reservoir["A2"].bottom(), slide_slot, new_tip="never", disposal_volume=0)
    pipette_1000.drop_tip()

    # anti-IgG incubation
    for minute_count in range(60, 0, -1):
        protocol.delay(minutes=1, msg=f"Incubating with biotinylated anti-IgG for 60 minutes - there are {minute_count} minutes left!")
    
    # PBST wash
    PBST_washes()

    # Dye addition
    pipette_1000.pick_up_tip()
    pipette_1000.mix(4, 700, reagent_reservoir["A3"])
    for slide_slot in required_slide_slots:
        pipette_1000.distribute(240, reagent_reservoir["A3"].bottom(), slide_slot, new_tip="never", disposal_volume=0)
    pipette_1000.drop_tip()

    # Dye incubation
    for minute_count in range(20, 0, -1):
        protocol.delay(minutes=1, msg=f"Incubating with dye for 20 minutes - there are {minute_count} minutes left!")
    
    # PBST wash
    PBST_washes()

    # Water wash
    def water_wash_single():
        for slide_slot in required_slide_slots:
            pipette_1000.distribute(240, water_reservoir["A1"].bottom(), slide_slot, new_tip="never", disposal_volume=0)
        protocol.delay(seconds=20)

    def water_washes():
        pipette_1000.pick_up_tip()
        for _ in range(8):
            water_wash_single()
        pipette_1000.drop_tip()

    water_washes()


def add_parameters(parameters):
    parameters.add_int(
        variable_name = "sample_count",
        display_name = "Sample count",
        description = "Number of input serum samples",
        default = 12,
        choices = [
            {"display_name": "6", "value": 6},
            {"display_name": "12", "value": 12},
            {"display_name": "18", "value": 18},
            {"display_name": "24", "value": 24},
            {"display_name": "30", "value": 30},
            {"display_name": "36", "value": 36},
            {"display_name": "40", "value": 40},
            {"display_name": "41", "value": 41},
            {"display_name": "42", "value": 42},
            {"display_name": "43", "value": 43},
            {"display_name": "44", "value": 44},
            {"display_name": "45", "value": 45},
            {"display_name": "46", "value": 46},
            {"display_name": "47", "value": 47},
            {"display_name": "48", "value": 48},
        ]
    )
