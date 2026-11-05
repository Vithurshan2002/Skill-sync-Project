<div class="ss-location-capture" x-data="{
    busy: false, message: '', captureVersion: 0,
    searchQuery: '', searchResults: [], searchMessage: '', searching: false, searchVersion: 0,
    searchUrl: @js(route('locations.search')), csrfToken: @js(csrf_token()),
    searchAddress() {}, cancelSearch() {}, chooseAddress() {},
    mapReady: false, mapWarning: '', disposed: false, mapCleanup: null,
    selectMapCenter() {},
    destroy() { this.disposed = true; this.captureVersion++; this.cancelSearch(); this.mapCleanup?.(); },
    statePath: @js($getStatePath()),
    worker: @js($forWorker),
    setField(field, value) { $wire.$set(this.statePath + '.' + field, value, false); },
    locate() {
        this.cancelSearch();
        if (!navigator.geolocation || !window.isSecureContext) {
            this.message = 'Location is unavailable in this browser. Select a point on the map, enter coordinates below, or continue with town matching.';
            return;
        }
        this.busy = true; this.message = 'Finding your location...';
        const version = ++this.captureVersion;
        navigator.geolocation.getCurrentPosition(position => {
            if (version !== this.captureVersion) return;
            this.busy = false;
            if (position.coords.accuracy > 1000) {
                this.message = 'The detected location is too imprecise. Select the correct point on the map or enter coordinates below.';
                return;
            }
            this.setField('latitude', Number(position.coords.latitude.toFixed(6)));
            this.setField('longitude', Number(position.coords.longitude.toFixed(6)));
            this.message = 'Location added to this form (accuracy about ' + Math.round(position.coords.accuracy) + ' m). Check the location before saving.';
        }, error => {
            if (version !== this.captureVersion) return;
            this.busy = false;
            this.message = error.code === 1 ? 'Location permission was denied. Select a point on the map, enter coordinates below, or continue with town matching.' : 'Unable to get your location. Select a point on the map or enter coordinates below.';
        }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 });
    },
    clearLocation() {
        this.cancelSearch(); this.searchQuery = ''; this.searchMessage = '';
        this.captureVersion++; this.busy = false;
        this.setField('latitude', null); this.setField('longitude', null);
        if (this.worker) this.setField('serviceRadiusKm', null);
        this.message = 'Location cleared from the form. Save to use town matching.';
    }
}" x-init="import(@js(\Illuminate\Support\Facades\Vite::asset('resources/js/location-map.js')))
    .then(() => window.SkillSyncMountLocationMap($data, $refs.locationMap, $wire, $watch))
    .catch(() => { mapWarning = 'Map is unavailable. Enter coordinates or continue with town matching.'; })">
    <p>{{ $forWorker ? 'Use your usual starting point for work. Your exact coordinates are not shown on your public profile.' : 'Select the place where the work is needed. The saved location is shared with your booked professional and administrators.' }} Search an address, click the map, or drag the pin to choose the correct place. Leave the location empty to use town matching.</p>
    <div class="ss-address-search" x-id="['address-query']">
        <label x-bind:for="$id('address-query')">Search address or place in Sri Lanka</label>
        <div class="ss-address-search-controls">
            <input type="search" x-bind:id="$id('address-query')" x-model="searchQuery" maxlength="200"
                placeholder="Street, town or landmark" autocomplete="off" x-on:input="cancelSearch(); searchMessage = ''"
                x-on:keydown.enter.prevent.stop="searchAddress()" x-on:keydown.escape.stop="cancelSearch()">
            <x-filament::button type="button" color="gray" x-on:click="searchAddress()" x-bind:disabled="searching || !mapReady">
                <span x-show="!searching">Search address</span><span x-show="searching" x-cloak>Searching...</span>
            </x-filament::button>
        </div>
        <p class="ss-address-help">Search sends this text to OpenStreetMap Nominatim. Use a street, town or landmark; omit personal or confidential details.</p>
        <p role="status" aria-live="polite" x-text="searchMessage" x-show="searchMessage" x-cloak></p>
        <ul class="ss-address-results" aria-label="Address search results" x-show="searchResults.length" x-cloak>
            <template x-for="(result, index) in searchResults" x-bind:key="index">
                <li><button type="button" x-on:click="chooseAddress(result)" x-text="result.label"></button></li>
            </template>
        </ul>
        <p class="ss-address-help">Search data &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a>.</p>
    </div>
    <div class="ss-location-actions">
        @if($forWorker)
            <x-filament::button type="button" color="gray" x-on:click="locate()" x-bind:disabled="busy" icon="heroicon-o-map-pin">Use current location</x-filament::button>
        @endif
        <button type="button" class="ss-text-link" x-on:click="clearLocation()">Clear location</button>
    </div>
    <div class="ss-location-map" x-ref="locationMap" wire:ignore role="region" aria-label="Location map" aria-description="Click to select a location. Drag the pin to adjust it. Use arrow keys to pan, then choose Use map centre."></div>
    <div class="ss-location-actions ss-map-actions" x-show="mapReady" x-cloak>
        <button type="button" class="ss-text-link" x-on:click="selectMapCenter()">Use map centre</button>
        <span>Zoom in to place the pin accurately.</span>
    </div>
    <p role="status" x-text="mapWarning" x-show="mapWarning" x-cloak></p>
    <p role="status" aria-live="polite" x-text="message" x-show="message" x-cloak></p>
    <p>Distance is an approximate straight line, not road distance or travel time.</p>
</div>
