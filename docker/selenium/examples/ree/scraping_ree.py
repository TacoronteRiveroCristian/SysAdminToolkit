#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import time
from datetime import datetime
from typing import Literal

import pandas as pd
import pytz
from ctrutils.database.influxdb.InfluxdbOperation import InfluxdbOperation
from ctrutils.handler.diagnostic.error_handler import ErrorHandler as error
from ctrutils.handler.logging.logging_handler import LoggingHandler
from selenium import webdriver
from selenium.common.exceptions import (
    ElementNotInteractableException,
    TimeoutException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from unidecode import unidecode

# Configure logging
logging_handler = LoggingHandler()
stream = logging_handler.create_stream_handler()
logger = logging_handler.add_handlers([stream])

# Get current date
current_date = datetime.now().strftime("%Y-%m-%d")


def _create_driver(headless: bool = True) -> webdriver.Chrome:
    """Returns a Chrome instance configured for Docker."""
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=opts)

    # Show versions to verify everything is OK
    caps = driver.capabilities
    logger.info(f"Chrome Version  : {caps['browserVersion']}")
    logger.info(f"ChromeDriver    : {driver.service.path}")
    return driver


def extract_tables(
    url: str,
    *,
    headless: bool = True,
) -> dict[Literal["demand", "generation", "emission"], pd.DataFrame]:
    """Returns the Demand, Generation, and Emission tables as DataFrames."""
    names = ("demand", "generation", "emission")
    dataframes: dict[str, pd.DataFrame] = {}
    canary_tz = pytz.timezone("Atlantic/Canary")

    driver = _create_driver(headless=headless)
    wait = WebDriverWait(driver, 10)

    try:
        driver.get(url)
        try:
            wait.until(
                EC.element_to_be_clickable(
                    (
                        By.ID,
                        "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
                    )
                )
            ).click()
        except TimeoutException:
            pass  # no banner appeared

        for name, idx in zip(names, range(1, 4)):
            # Buttons for the three tables
            buttons = wait.until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "ul.pagination-menu > li > a")
                )
            )
            button = buttons[idx - 1]

            # Ensure scroll and click
            driver.execute_script("arguments[0].scrollIntoView(true);", button)
            try:
                button.click()
            except ElementNotInteractableException:
                driver.execute_script("arguments[0].click();", button)

            # Add 1 second delay to ensure page loads properly
            time.sleep(1)

            # Wait for the corresponding table to become visible
            table = wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "div.tabla-evolucion-content")
                )
            )

            # Header
            header_raw = table.find_elements(By.CSS_SELECTOR, "tbody > tr > th")
            header = [
                unidecode(th.text.lower()).replace(" ", "_")
                for th in header_raw
            ]

            # Data rows
            rows = table.find_elements(By.CSS_SELECTOR, "tbody > tr")
            row_data: list[list[str | float]] = []

            logger.info(f"Table {name} has {len(rows)} rows")
            logger.info(f"Header: {header}")

            for row in rows[1:]:  # skip header
                cells = row.find_elements(By.CSS_SELECTOR, "td")
                if not cells:
                    continue

                try:
                    date = datetime.strptime(
                        cells[0].text.strip(), "%Y-%m-%d %H:%M"
                    )
                    values: list[str | float] = [canary_tz.localize(date)]
                    for cell in cells[1:]:
                        # Replace commas with dots and handle missing values
                        # with -999 for identification and handling
                        text = cell.text.strip().replace(",", ".") or "-999"
                        values.append(float(text))
                    row_data.append(values)
                except (IndexError, ValueError):
                    logger.warning("Row with unexpected format; skipping.")
                    continue

            if not row_data:
                logger.warning(f"No data for table {name}")
                continue

            df = (
                pd.DataFrame(row_data, columns=header)
                .set_index("hora")
                .sort_index()
            )
            dataframes[name] = df
    finally:
        driver.quit()

    return dataframes


def main(current_date: str) -> None:
    """Main function to scrape REE data."""
    url = (
        "https://demanda.ree.es/visiona/canarias/la_gomera5m/"
        f"tablas/{current_date}/1"
    )

    logger.info(f"Extracting data from {url}")
    dfs = extract_tables(url, headless=True)

    for name, df in dfs.items():
        # Replace -999 values with NaN
        df = df.replace(-999, float("nan"))

        logger.info(f"DataFrame {name}:")
        logger.info(df)


if __name__ == "__main__":
    try:
        main(current_date)
    except Exception as e:
        error_msg = f"Error running the script: {e}"
        error.throw_error(error_msg, logger)
