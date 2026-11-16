const searchMenu =
    document.getElementById("searchMenu");

const searchOptions =
    document.getElementById("searchOptions");

const trendOptions =
    document.querySelectorAll(".trend-option");

const historyButton =
    document.getElementById("historyButton");

const savedButton =
    document.getElementById("savedButton");

const results =
    document.getElementById("results");


// Stores the latest successful search

let currentTrendData = null;


// --------------------------------
// REGION SELECTOR (added by script)
// --------------------------------

const REGION_OPTIONS = [
    ["south", "Tamil Nadu + Karnataka"],
    ["tn", "Tamil Nadu"],
    ["ka", "Karnataka"]
];

let selectedRegion = "south";
let lastCategory = null;

(function addRegionSelector() {

    if (!results || !results.parentNode) return;

    const box = document.createElement("div");
    box.style.cssText = "text-align:center;margin:18px 0 0;";

    const label = document.createElement("label");
    label.textContent = "📍 Region: ";
    label.htmlFor = "regionSelect";

    const select = document.createElement("select");
    select.id = "regionSelect";
    select.style.cssText =
        "padding:8px 14px;border-radius:10px;border:1px solid #ddd;font:inherit;";

    REGION_OPTIONS.forEach(([value, text]) => {
        const o = document.createElement("option");
        o.value = value;
        o.textContent = text;
        select.appendChild(o);
    });

    // Changing region re-runs the last search
    select.addEventListener("change", () => {
        selectedRegion = select.value;
        if (lastCategory) {
            const opt = document.querySelector(
                `.trend-option[data-category="${lastCategory}"]`
            );
            if (opt) opt.click();
        }
    });

    box.append(label, select);
    results.parentNode.insertBefore(box, results);

})();


// --------------------------------
// SEARCH DROPDOWN
// --------------------------------

if (searchMenu) {

    searchMenu.addEventListener(
        "click",
        () => {

            searchOptions.classList.toggle(
                "show"
            );

        }
    );

}


// --------------------------------
// SEARCH OPTIONS
// --------------------------------

trendOptions.forEach(
    (option) => {

        option.addEventListener(
            "click",
            async () => {

                const category =
                    option.dataset.category;

                lastCategory = category;


                searchOptions.classList.remove(
                    "show"
                );


                results.innerHTML = `
                    <h2>
                        🔄 Loading live trends...
                    </h2>

                    <p>
                        Fetching current data from
                        Google Trends.
                    </p>
                `;


                try {

                    const response =
                        await fetch(
                            `/api/trends/${category}?region=${selectedRegion}`
                        );


                    const data =
                        await response.json();


                    // API ERROR

                    if (!response.ok) {

                        results.innerHTML = `
                            <h2>
                                ⚠️ Live Trends Unavailable
                            </h2>

                            <p>
                                ${data.message ||
                                "Please try again later."}
                            </p>
                        `;

                        return;

                    }


                    // SUCCESS

                    currentTrendData = data;

                    displayResults(
                        data
                    );


                }

                catch (error) {

                    console.error(
                        "Trend Error:",
                        error
                    );


                    results.innerHTML = `
                        <h2>
                            ⚠️ Error Loading Trends
                        </h2>

                        <p>
                            Please check your connection
                            and try again.
                        </p>
                    `;

                }

            }
        );

    }
);


// --------------------------------
// HISTORY
// --------------------------------

if (historyButton) {

    historyButton.addEventListener(
        "click",
        loadHistory
    );

}


async function loadHistory() {

    currentTrendData = null;


    results.innerHTML = `
        <h2>
            🕒 Search History
        </h2>

        <p>
            Loading history...
        </p>
    `;


    try {

        const response =
            await fetch(
                "/api/history"
            );


        const history =
            await response.json();


        results.innerHTML = `
            <h2>
                🕒 Search History
            </h2>
        `;


        if (!history.length) {

            results.innerHTML += `
                <p>
                    No search history yet.
                </p>
            `;

            return;

        }


        history.forEach(
            (item) => {

                results.innerHTML += `

                    <div class="trend-card">

                        <h3>
                            ${item.category.toUpperCase()}
                        </h3>

                        <p>
                            📅 ${item.searched_at}
                        </p>

                    </div>

                `;

            }
        );


    }

    catch (error) {

        console.error(
            "History Error:",
            error
        );


        results.innerHTML = `
            <h2>
                ⚠️ Error Loading History
            </h2>
        `;

    }

}


// --------------------------------
// SAVED BUTTON
// --------------------------------

if (savedButton) {

    savedButton.addEventListener(
        "click",
        async () => {


            // SAVE CURRENT RESULTS

            if (currentTrendData) {

                await saveCurrentTrend();

            }


            // SHOW SAVED TRENDS

            else {

                loadSavedTrends();

            }

        }
    );

}


// --------------------------------
// SAVE CURRENT TREND
// --------------------------------

async function saveCurrentTrend() {

    try {

        const response =
            await fetch(
                "/api/save",
                {

                    method: "POST",

                    headers: {

                        "Content-Type":
                            "application/json"

                    },

                    body: JSON.stringify({

                        category:
                            currentTrendData.category,

                        results:
                            currentTrendData

                    })

                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.message
            );

        }


        results.innerHTML = `

            <h2>
                🔖 Trend Saved Successfully!
            </h2>

            <p>
                Category:
                ${currentTrendData.category}
            </p>

            <p>
                📅 Saved just now
            </p>

            <button
                id="viewSavedButton"
            >
                View Saved Trends
            </button>

        `;


        currentTrendData = null;


        document
            .getElementById(
                "viewSavedButton"
            )
            .addEventListener(
                "click",
                loadSavedTrends
            );


    }

    catch (error) {

        console.error(
            "Save Error:",
            error
        );


        results.innerHTML = `
            <h2>
                ⚠️ Error Saving Trend
            </h2>

            <p>
                Please try again.
            </p>
        `;

    }

}


// --------------------------------
// LOAD SAVED TRENDS
// --------------------------------

async function loadSavedTrends() {

    results.innerHTML = `
        <h2>
            🔖 Saved Trends
        </h2>

        <p>
            Loading saved trends...
        </p>
    `;


    try {

        const response =
            await fetch(
                "/api/saved"
            );


        const savedTrends =
            await response.json();


        displaySavedTrends(
            savedTrends
        );


    }

    catch (error) {

        console.error(
            "Saved Error:",
            error
        );


        results.innerHTML = `
            <h2>
                ⚠️ Error Loading Saved Trends
            </h2>
        `;

    }

}


// --------------------------------
// DISPLAY SAVED TRENDS
// --------------------------------

function displaySavedTrends(savedTrends) {

    results.innerHTML = `
        <h2>
            🔖 Saved Trends
        </h2>
    `;


    if (!savedTrends.length) {

        results.innerHTML += `
            <p>
                No saved trends yet.
            </p>
        `;

        return;

    }


    savedTrends.forEach(
        (item) => {

            results.innerHTML += `

                <div class="trend-card">

                    <h2>
                        ${item.category}
                    </h2>

                    <p>
                        📅 ${item.saved_at}
                    </p>

                    <button
                        class="view-saved"
                        data-id="${item.id}"
                    >
                        View Results
                    </button>

                </div>

            `;

        }
    );


    document
        .querySelectorAll(
            ".view-saved"
        )
        .forEach(
            (button) => {

                button.addEventListener(
                    "click",
                    () => {

                        const item =
                            savedTrends.find(
                                (trend) =>

                                    trend.id ==
                                    button.dataset.id
                            );


                        if (!item) {

                            return;

                        }


                        const trendData =
                            JSON.parse(
                                item.trend_data
                            );


                        currentTrendData =
                            trendData;


                        displayResults(
                            trendData
                        );

                    }
                );

            }
        );

}


// --------------------------------
// DISPLAY TREND RESULTS
// --------------------------------

function displayResults(data) {

    renderResults(data);

    if (data.region) {

        let note = `📍 ${data.region}`;

        if (data.partial) {
            note += ` (partial: ${data.regions_included.join(", ")} so far)`;
        }

        results.innerHTML = `<p>${note}</p>` + results.innerHTML;

    }

    if (data.updated_at) {

        results.innerHTML += `
            <p>
                🕒 Data last updated:
                ${data.updated_at} UTC
            </p>
        `;

    }

}


function renderResults(data) {

    results.innerHTML = "";


    // COLORS

    if (
        data.category ===
        "Colors"
    ) {

        results.innerHTML = `
            <h2>
                🎨 Trending Colors
            </h2>
        `;


        displayCards(
            data.results
        );

    }


    // FABRICS

    else if (
        data.category ===
        "Fabrics"
    ) {

        results.innerHTML = `
            <h2>
                🧵 Trending Fabrics
            </h2>
        `;


        displayCards(
            data.results
        );

    }


    // BOTH

    else if (
        data.category ===
        "Both"
    ) {

        results.innerHTML = `
            <h2>
                🎨 Trending Colors
            </h2>
        `;


        displayCards(
            data.colors
        );


        results.innerHTML += `
            <h2>
                🧵 Trending Fabrics
            </h2>
        `;


        displayCards(
            data.fabrics
        );

    }

}


// --------------------------------
// DISPLAY CARDS
// --------------------------------

function displayCards(items) {

    items.forEach(
        (item, index) => {

            results.innerHTML += `

                <div class="trend-card">

                    <h3>
                        #${index + 1}
                    </h3>

                    <h2>
                        ${item.name}
                    </h2>

                    <p>
                        Trend Score:
                        ${item.score}
                    </p>

                </div>

            `;

        }
    );

}