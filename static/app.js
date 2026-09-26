// ======================================================
// BUSMATE STUDENT PORTAL
// ======================================================


// ======================================================
// HTML ESCAPE
// ======================================================

function escapeHTML(value) {

    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


// ======================================================
// PORTAL NOTICES
// ======================================================

async function loadPortalNotices(containerId) {

    const container = document.getElementById(containerId);

    if (!container) return;

    container.innerHTML = '<div class="notice-empty">🔄 Loading notices...</div>';

    try {
        const response = await fetch("/api/notices");
        const data = await response.json();

        if (!data.success || !Array.isArray(data.notices) || data.notices.length === 0) {
            container.innerHTML = '<div class="notice-empty">📢 No new transport notices.</div>';
            return;
        }

        container.innerHTML = data.notices.map(function(notice) {

            const priority = String(notice.priority || "NORMAL").toLowerCase();

            return `
                <article class="notice-card notice-${escapeHTML(priority)}">
                    <div class="notice-card-header">
                        <h4>📢 ${escapeHTML(notice.title)}</h4>
                        <span class="notice-priority ${escapeHTML(priority)}">
                            ${escapeHTML(notice.priority || "NORMAL")}
                        </span>
                    </div>

                    <p>${escapeHTML(notice.message)}</p>

                    <div class="notice-meta">
                        ${escapeHTML(notice.created_at || "")}
                    </div>
                </article>
            `;

        }).join("");

    } catch (error) {
        console.error("Notice load error:", error);
        container.innerHTML = '<div class="notice-empty">Unable to load notices. Please try again.</div>';
    }
}


// ======================================================
// LOAD ALL BUS ROUTES
// IMPORTANT:
// Stops are NOT loaded here.
// Stops load only when user clicks
// "View Boarding Points".
// ======================================================

async function loadRoutesWithStops() {

    const container =
        document.getElementById("routeList");


    if (!container) {
        return;
    }


    container.innerHTML =
        '<p class="loading">🚌 Loading bus routes...</p>';


    try {

        const response =
            await fetch("/api/buses", {
                method: "GET",
                headers: {
                    "Accept": "application/json"
                }
            });


        if (!response.ok) {

            throw new Error(
                "HTTP " + response.status
            );

        }


        const data =
            await response.json();


        container.innerHTML = "";


        if (
            !data.success ||
            !Array.isArray(data.buses) ||
            data.buses.length === 0
        ) {

            container.innerHTML = `
                <div class="empty-card">
                    🚌 No bus routes available.
                </div>
            `;

            return;
        }


        data.buses.forEach(function(bus) {

            const busNumber =
                bus.bus_number || "---";


            const routeName =
                bus.route_name || "Route not available";


            const card =
                document.createElement("div");


            card.className =
                "route-card";


            card.innerHTML = `

                <div class="route-card-header">

                    <div>

                        <h3>
                            🚌 ${escapeHTML(busNumber)}
                        </h3>

                        <p class="route-name">
                            ${escapeHTML(routeName)}
                        </p>

                    </div>

                </div>


                <div class="route-details">

                    <p>
                        🛣️
                        <strong>Route:</strong>
                        ${escapeHTML(routeName)}
                    </p>


                    <button
                        type="button"
                        class="boarding-toggle">

                        📍 View Boarding Points

                    </button>


                    <div class="boarding-panel">

                        <h4 class="boarding-title">

                            📍 Boarding Points -
                            ${escapeHTML(busNumber)}

                        </h4>


                        <div class="boarding-points">

                        </div>

                    </div>

                </div>

            `;


            container.appendChild(card);


            const button =
                card.querySelector(
                    ".boarding-toggle"
                );


            const panel =
                card.querySelector(
                    ".boarding-panel"
                );


            const stopsContainer =
                card.querySelector(
                    ".boarding-points"
                );


            // ------------------------------------------------
            // BUTTON CLICK
            // ------------------------------------------------

            button.addEventListener(
                "click",
                function() {

                    toggleBoardingPoints(
                        busNumber,
                        button,
                        panel,
                        stopsContainer
                    );

                }
            );

        });


    } catch (error) {

        console.error(
            "Bus route error:",
            error
        );


        container.innerHTML = `

            <div class="error-box">

                ❌ Unable to load bus routes.

                <br><br>

                Please try again.

            </div>

        `;

    }

}


// ======================================================
// TOGGLE BOARDING POINTS
// ======================================================

async function toggleBoardingPoints(
    busNumber,
    button,
    panel,
    stopsContainer
) {


    // -----------------------------------------------
    // If already visible -> hide
    // -----------------------------------------------

    if (
        panel.classList.contains("show")
    ) {

        panel.classList.remove("show");

        button.textContent =
            "📍 View Boarding Points";

        return;
    }


    // -----------------------------------------------
    // Show panel
    // -----------------------------------------------

    panel.classList.add("show");


    button.textContent =
        "🔼 Hide Boarding Points";


    // -----------------------------------------------
    // If already loaded, don't fetch again
    // -----------------------------------------------

    if (
        panel.dataset.loaded === "true"
    ) {

        return;
    }


    button.classList.add("loading");

    button.textContent =
        "⏳ Loading Boarding Points...";


    stopsContainer.innerHTML = `

        <p class="loading">
            📍 Loading ${escapeHTML(busNumber)} stops...
        </p>

    `;


    try {

        const response =
            await fetch(
                `/api/bus/${encodeURIComponent(busNumber)}/stops`,
                {
                    method: "GET",
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );


        if (!response.ok) {

            throw new Error(
                "HTTP " + response.status
            );

        }


        const data =
            await response.json();


        stopsContainer.innerHTML = "";


        // -------------------------------------------
        // No stops
        // -------------------------------------------

        if (
            !data.success ||
            !Array.isArray(data.stops) ||
            data.stops.length === 0
        ) {

            stopsContainer.innerHTML = `

                <div class="empty-card">

                    📍 No boarding points available
                    for
                    <strong>
                        ${escapeHTML(busNumber)}
                    </strong>.

                </div>

            `;

        }


        // -------------------------------------------
        // Display only THIS bus stops
        // -------------------------------------------

        else {

            data.stops.forEach(
                function(stop, index) {

                    const item =
                        document.createElement("div");


                    item.className =
                        "stop-item";


                    const stopName =
                        stop.stop_name ||
                        "Unknown stop";


                    const stopTime =
                        stop.stop_time ||
                        "";


                    item.innerHTML = `

                        <span class="stop-icon">

                            📍

                        </span>


                        <div class="stop-info">

                            <strong>

                                ${index + 1}.
                                ${escapeHTML(stopName)}

                            </strong>


                            ${
                                stopTime
                                ?
                                `
                                <small>

                                    🕐
                                    ${escapeHTML(stopTime)}

                                </small>
                                `
                                :
                                ""
                            }

                        </div>

                    `;


                    stopsContainer.appendChild(
                        item
                    );

                }
            );

        }


        panel.dataset.loaded = "true";


        button.classList.remove(
            "loading"
        );


        button.textContent =
            "🔼 Hide Boarding Points";


    } catch (error) {

        console.error(
            "Boarding points error:",
            error
        );


        stopsContainer.innerHTML = `

            <div class="error-box">

                ❌ Unable to load boarding points.

                <br>

                Please try again.

            </div>

        `;


        button.classList.remove(
            "loading"
        );


        button.textContent =
            "📍 View Boarding Points";

    }

}


// ======================================================
// SEARCH BUS BY BOARDING POINT
// ======================================================

async function searchBoardingPoint() {

    const input =
        document.getElementById(
            "boardingPoint"
        );


    const result =
        document.getElementById(
            "searchResults"
        );


    if (!input || !result) {
        return;
    }


    const stop =
        input.value.trim();


    if (!stop) {

        result.innerHTML = `

            <div class="warning-box">

                ⚠️ Please enter a boarding point.

            </div>

        `;

        return;
    }


    result.innerHTML = `

        <p class="loading">

            🔍 Searching...

        </p>

    `;


    try {

        const response =
            await fetch(
                `/api/search?stop=${encodeURIComponent(stop)}`,
                {
                    method: "GET",
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );


        if (!response.ok) {

            throw new Error(
                "HTTP " + response.status
            );

        }


        const data =
            await response.json();


        result.innerHTML = "";


        if (
            !data.success ||
            !Array.isArray(data.results) ||
            data.results.length === 0
        ) {

            result.innerHTML = `

                <div class="empty-card">

                    🚌 No bus found for

                    <strong>
                        ${escapeHTML(stop)}
                    </strong>.

                </div>

            `;

            return;
        }


        data.results.forEach(
            function(bus) {

                const card =
                    document.createElement("div");


                card.className =
                    "route-card";


                card.innerHTML = `

                    <div class="route-card-header">

                        <div>

                            <h3>

                                🚌
                                ${escapeHTML(
                                    bus.bus_number || "---"
                                )}

                            </h3>


                            <p class="route-name">

                                ${escapeHTML(
                                    bus.route_name || "---"
                                )}

                            </p>

                        </div>

                    </div>


                    <div class="route-details">

                        <p>

                            📍
                            <strong>
                                Boarding:
                            </strong>

                            ${escapeHTML(
                                bus.stop_name || stop
                            )}

                        </p>


                        <p>

                            🕐
                            <strong>
                                Time:
                            </strong>

                            ${escapeHTML(
                                bus.stop_time ||
                                "Not available"
                            )}

                        </p>

                    </div>

                `;


                result.appendChild(card);

            }
        );


    } catch (error) {

        console.error(
            "Search error:",
            error
        );


        result.innerHTML = `

            <div class="error-box">

                ❌ Error searching boarding point.

            </div>

        `;

    }

}


// ======================================================
// RETURN BUSES
// ======================================================

async function loadReturnBuses() {

    const container =
        document.getElementById(
            "returnBusList"
        );


    if (!container) {
        return;
    }


    container.innerHTML =
        '<p class="loading">🔄 Loading return buses...</p>';


    try {

        const response =
            await fetch(
                "/api/return-buses",
                {
                    method: "GET",
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );


        if (!response.ok) {

            throw new Error(
                "HTTP " + response.status
            );

        }


        const data =
            await response.json();


        container.innerHTML = "";


        if (
            !data.success ||
            !Array.isArray(data.buses) ||
            data.buses.length === 0
        ) {

            container.innerHTML = `

                <div class="empty-card">

                    🔄 No return buses available.

                </div>

            `;

            return;
        }


        data.buses.forEach(
            function(bus) {

                const card =
                    document.createElement("div");


                card.className =
                    "route-card";


                const departure =
                    bus.departure_time ||
                    data.default_time ||
                    "3:50 PM";


                card.innerHTML = `

                    <div class="route-card-header">

                        <div>

                            <h3>

                                🚌
                                ${escapeHTML(
                                    bus.bus_number || "---"
                                )}

                            </h3>


                            <p class="route-name">

                                ${escapeHTML(
                                    bus.route_name || "---"
                                )}

                            </p>

                        </div>


                        <span class="time-badge">

                            ${escapeHTML(departure)}

                        </span>

                    </div>


                    <div class="route-details">

                        <p>

                            🛣️
                            <strong>
                                Route:
                            </strong>

                            ${escapeHTML(
                                bus.route_name || "---"
                            )}

                        </p>


                        <p>

                            🕐
                            <strong>
                                Departure:
                            </strong>

                            <span class="highlight">

                                ${escapeHTML(departure)}

                            </span>

                        </p>

                    </div>

                `;


                container.appendChild(card);

            }
        );


    } catch (error) {

        console.error(
            "Return bus error:",
            error
        );


        container.innerHTML = `

            <div class="error-box">

                ❌ Error loading return buses.

            </div>

        `;

    }

}


// ======================================================
// EXAM TIME BUSES
// ======================================================

async function loadExamBuses() {

    const input =
        document.getElementById(
            "examDate"
        );


    const container =
        document.getElementById(
            "examBusList"
        );


    if (!input || !container) {
        return;
    }


    const htmlDate =
        input.value;


    if (!htmlDate) {

        alert(
            "Please select exam date."
        );

        return;
    }


    const parts =
        htmlDate.split("-");


    const formattedDate =
        `${parts[2]}-${parts[1]}-${parts[0]}`;


    container.innerHTML = `

        <p class="loading">

            📝 Loading exam buses for
            ${escapeHTML(formattedDate)}...

        </p>

    `;


    try {

        const response =
            await fetch(
                `/api/exam-buses?date=${encodeURIComponent(
                    formattedDate
                )}`,
                {
                    method: "GET",
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );


        if (!response.ok) {

            throw new Error(
                "HTTP " + response.status
            );

        }


        const data =
            await response.json();


        container.innerHTML = "";


        if (
            !data.success ||
            !Array.isArray(data.buses) ||
            data.buses.length === 0
        ) {

            container.innerHTML = `

                <div class="empty-card">

                    <h3>
                        📝 No Exam Time Buses
                    </h3>

                    <p>

                        No exam buses available for

                        <strong>
                            ${escapeHTML(
                                formattedDate
                            )}
                        </strong>.

                    </p>

                </div>

            `;

            return;
        }


        data.buses.forEach(
            function(bus) {

                const card =
                    document.createElement("div");


                card.className =
                    "route-card";


                card.innerHTML = `

                    <div class="route-card-header">

                        <div>

                            <h3>

                                📝
                                ${escapeHTML(
                                    bus.bus_number || "---"
                                )}

                            </h3>


                            <p class="route-name">

                                ${escapeHTML(
                                    bus.route_name || "---"
                                )}

                            </p>

                        </div>


                        <span class="time-badge">

                            ${escapeHTML(
                                bus.departure_time || "---"
                            )}

                        </span>

                    </div>


                    <div class="route-details">

                        <p>

                            🛣️
                            <strong>
                                Route:
                            </strong>

                            ${escapeHTML(
                                bus.route_name || "---"
                            )}

                        </p>


                        <p>

                            🕐
                            <strong>
                                Departure:
                            </strong>

                            <span class="highlight">

                                ${escapeHTML(
                                    bus.departure_time || "---"
                                )}

                            </span>

                        </p>


                        <p>

                            📍
                            <strong>
                                Destination:
                            </strong>

                            ${escapeHTML(
                                bus.destination || "---"
                            )}

                        </p>


                        <p>

                            📅
                            <strong>
                                Date:
                            </strong>

                            ${escapeHTML(
                                bus.travel_date ||
                                formattedDate
                            )}

                        </p>

                    </div>

                `;


                container.appendChild(card);

            }
        );


    } catch (error) {

        console.error(
            "Exam bus error:",
            error
        );


        container.innerHTML = `

            <div class="error-box">

                ❌ Error loading exam buses.

            </div>

        `;

    }

}


// ======================================================
// LIVE BUS TRACKING
// ======================================================

async function showLiveBus() {

    const input =
        document.getElementById(
            "liveBusNumber"
        );


    const result =
        document.getElementById(
            "liveBusResult"
        );


    if (!input || !result) {
        return;
    }


    const busNumber =
        input.value
            .trim()
            .toUpperCase();


    if (!busNumber) {

        alert(
            "Please enter bus number."
        );

        return;
    }


    result.innerHTML = `

        <p class="loading">

            📍 Checking live location...

        </p>

    `;


    try {

        const response =
            await fetch(
                `/api/bus-location/${encodeURIComponent(
                    busNumber
                )}`,
                {
                    method: "GET",
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );


        if (!response.ok) {

            throw new Error(
                "HTTP " + response.status
            );

        }


        const data =
            await response.json();


        if (!data.success) {

            result.innerHTML = `

                <div class="empty-card">

                    🚌 Bus

                    <strong>
                        ${escapeHTML(busNumber)}
                    </strong>

                    not found.

                </div>

            `;

            return;
        }


        result.innerHTML = `

            <div class="route-card">

                <div class="route-card-header">

                    <div>

                        <h3>

                            🚌
                            ${escapeHTML(
                                data.bus_number ||
                                busNumber
                            )}

                        </h3>


                        <p class="route-name">

                            ${escapeHTML(
                                data.route_name || "---"
                            )}

                        </p>

                    </div>

                </div>


                <div class="driver-live-details" style="margin:12px 0;padding:12px;border:1px solid #dbe7f3;border-radius:10px;background:#f8fbff;">
                    ${data.location_shared && data.driver_name
                        ? `<strong>👨‍✈️ Driver:</strong> ${escapeHTML(data.driver_name)} &nbsp; <strong>📞</strong> ${escapeHTML(data.driver_phone || "---")}`
                        : `<strong>👨‍✈️ Driver:</strong> Not currently sharing location`}
                </div>


                <div class="live-status">

                    ${
                        data.location_shared

                        ?

                        `
                        <span class="status-online">

                            🟢 Live location available

                        </span>
                        `

                        :

                        `
                        <span class="status-offline">

                            🔴 Driver has not shared
                            location yet

                        </span>
                        `
                    }

                </div>


                ${
                    data.location_shared

                    ?

                    `

                    <div class="location-details">

                        <div class="location-item">

                            <span>
                                Latitude
                            </span>

                            <strong>
                                ${escapeHTML(
                                    data.latitude
                                )}
                            </strong>

                        </div>


                        <div class="location-item">

                            <span>
                                Longitude
                            </span>

                            <strong>
                                ${escapeHTML(
                                    data.longitude
                                )}
                            </strong>

                        </div>


                        <div class="location-item">

                            <span>
                                Current Location
                            </span>

                            <strong>
                                ${escapeHTML(
                                    data.current_location ||
                                    "---"
                                )}
                            </strong>

                        </div>


                        <div class="location-item">

                            <span>
                                Next Point
                            </span>

                            <strong>
                                ${escapeHTML(
                                    data.next_point ||
                                    "---"
                                )}
                            </strong>

                        </div>


                        <div class="location-item">

                            <span>
                                Last Updated
                            </span>

                            <strong>
                                ${escapeHTML(
                                    data.updated_at ||
                                    "---"
                                )}
                            </strong>

                        </div>

                    </div>


                    <button
                        type="button"
                        class="map-btn"
                        onclick="openLiveMap('${escapeHTML(
                            data.bus_number ||
                            busNumber
                        )}')">

                        🗺️ Open Live Map

                    </button>

                    `

                    :

                    `

                    <div class="warning-box">

                        📍 Live location will appear
                        when the driver shares it.

                    </div>

                    `

                }

            </div>

        `;


    } catch (error) {

        console.error(
            "Live bus error:",
            error
        );


        result.innerHTML = `

            <div class="error-box">

                ❌ Unable to connect to server.

            </div>

        `;

    }

}


// ======================================================
// OPEN LIVE MAP
// ======================================================

function openLiveMap(busNumber) {

    window.location.href =
        `/live-map.html?bus=${encodeURIComponent(
            busNumber
        )}`;

}


// ======================================================
// PAGE EVENTS
// ======================================================

document.addEventListener(
    "DOMContentLoaded",
    function() {


        // ----------------------------------------------
        // Boarding point search
        // ----------------------------------------------

        const searchButton =
            document.getElementById(
                "searchBusButton"
            );


        if (searchButton) {

            searchButton.addEventListener(
                "click",
                searchBoardingPoint
            );

        }


        const searchInput =
            document.getElementById(
                "boardingPoint"
            );


        if (searchInput) {

            searchInput.addEventListener(
                "keydown",
                function(event) {

                    if (
                        event.key === "Enter"
                    ) {

                        event.preventDefault();

                        searchBoardingPoint();

                    }

                }
            );

        }


        // ----------------------------------------------
        // Live bus Enter
        // ----------------------------------------------

        const noticeList =
            document.getElementById(
                "studentNoticeList"
            );

        if (noticeList) {
            loadPortalNotices("studentNoticeList");
        }


        const liveInput =
            document.getElementById(
                "liveBusNumber"
            );


        if (liveInput) {

            liveInput.addEventListener(
                "keydown",
                function(event) {

                    if (
                        event.key === "Enter"
                    ) {

                        event.preventDefault();

                        showLiveBus();

                    }

                }
            );

        }

    }
);