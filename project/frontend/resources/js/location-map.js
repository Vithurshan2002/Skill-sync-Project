import L from 'leaflet';

// Keep Leaflet objects outside Alpine's reactive proxies.
window.SkillSyncMountLocationMap = function (component, host, wire, watch) {
    if (component.disposed) return;
    const map = L.map(host, { scrollWheelZoom: false, worldCopyJump: true })
        .setView([7.8731, 80.7718], 7);
    let marker = null;
    let circle = null;
    let lastCoordinates = '';
    let removed = false;
    let searchController = null;
    const number = value => value === null || value === undefined || value === '' ? null : Number(value);
    const read = field => number(wire.$get(component.statePath + '.' + field));
    const coordinates = () => {
        const lat = read('latitude'), lng = read('longitude');
        return Number.isFinite(lat) && Number.isFinite(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180 ? [lat, lng] : null;
    };
    const icon = L.divIcon({
        className: 'ss-map-marker',
        html: '<span class="ss-map-pin" aria-hidden="true"></span>',
        iconSize: [30, 40], iconAnchor: [15, 40],
    });
    const select = latlng => {
        component.cancelSearch();
        component.captureVersion++;
        component.busy = false;
        component.setField('latitude', Number(latlng.lat.toFixed(6)));
        component.setField('longitude', Number(latlng.wrap().lng.toFixed(6)));
        component.message = 'Location selected. Save the form to keep this change.';
        sync(false);
    };
    const sync = (recenter = true) => {
        if (removed) return;
        const position = coordinates();
        if (!position) {
            if (marker) map.removeLayer(marker);
            if (circle) map.removeLayer(circle);
            marker = circle = null;
            lastCoordinates = '';
            return;
        }
        if (!marker) {
            marker = L.marker(position, { icon, draggable: true, title: 'Selected location: drag to move', alt: 'Selected location' }).addTo(map);
            marker.on('dragend', () => select(marker.getLatLng()));
        } else {
            marker.setLatLng(position);
        }
        const radius = component.worker ? read('serviceRadiusKm') : null;
        if (Number.isFinite(radius) && radius >= 0.1 && radius <= 500) {
            if (!circle) circle = L.circle(position, { radius: radius * 1000, color: '#5141df', weight: 2, fillOpacity: 0.08, interactive: false }).addTo(map);
            circle.setLatLng(position).setRadius(radius * 1000);
        } else if (circle) {
            map.removeLayer(circle);
            circle = null;
        }
        const key = position.join(',');
        if (recenter && key !== lastCoordinates) map.setView(position, 13, { animate: false });
        lastCoordinates = key;
    };
    component.cancelSearch = () => {
        component.searchVersion++;
        searchController?.abort();
        searchController = null;
        component.searching = false;
        component.searchResults = [];
        component.searchMessage = '';
    };
    component.searchAddress = async () => {
        if (!component.mapReady) return;
        component.cancelSearch();
        const query = component.searchQuery.trim();
        if (query.length < 3) {
            component.searchMessage = 'Enter at least three characters to search.';
            return;
        }
        const version = component.searchVersion;
        searchController = new AbortController();
        component.searching = true;
        component.searchMessage = '';
        try {
            const response = await fetch(component.searchUrl, {
                method: 'POST', credentials: 'same-origin', signal: searchController.signal,
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', 'X-CSRF-TOKEN': component.csrfToken },
                body: JSON.stringify({ query }),
            });
            const data = await response.json();
            if (component.disposed || version !== component.searchVersion) return;
            if (!response.ok) {
                component.searchMessage = response.status === 401 || response.status === 419
                    ? 'Your session has expired. Refresh this page and sign in again.'
                    : response.status === 429 ? 'Address search is busy. Please wait a moment and search again.'
                    : 'Address search is unavailable. Select a point on the map.';
                return;
            }
            component.searchResults = Array.isArray(data.data) ? data.data : [];
            component.searchMessage = component.searchResults.length
                ? 'Choose a result, then check the pin before saving.'
                : 'No places found. Try a nearby street, town or landmark, or select a point on the map.';
        } catch (error) {
            if (error.name !== 'AbortError' && !component.disposed && version === component.searchVersion) {
                component.searchMessage = 'Address search is unavailable. Select a point on the map.';
            }
        } finally {
            if (version === component.searchVersion) component.searching = false;
        }
    };
    component.chooseAddress = result => {
        if (!Number.isFinite(result.latitude) || !Number.isFinite(result.longitude)
            || Math.abs(result.latitude) > 90 || Math.abs(result.longitude) > 180) return;
        select(L.latLng(result.latitude, result.longitude));
        map.setView([result.latitude, result.longitude], 16, { animate: false });
        component.searchQuery = result.label.slice(0, 200);
        component.message = 'Place selected. Adjust the pin if needed, then save the form.';
    };
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).on('tileerror', () => {
        component.mapWarning = 'Map imagery could not load. You can still enter coordinates or use town matching.';
    }).addTo(map);
    map.on('click', event => select(event.latlng));
    component.selectMapCenter = () => select(map.getCenter());
    watch(() => ['latitude', 'longitude', 'serviceRadiusKm']
        .map(field => wire.$get(component.statePath + '.' + field) ?? '').join('|'), () => sync());
    const observer = new ResizeObserver(() => map.invalidateSize({ pan: false }));
    observer.observe(host);
    component.mapCleanup = () => {
        removed = true;
        observer.disconnect();
        map.remove();
    };
    sync();
    component.mapReady = true;
};
