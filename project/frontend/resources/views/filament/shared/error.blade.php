@if($gatewayError)
    <div role="alert" class="ss-alert ss-alert-error">{{ $gatewayError }}</div>
@endif
@if($errors->any())
    <div role="alert" class="ss-alert ss-alert-error" tabindex="-1" x-data x-init="$el.focus()">
        <strong>Please check the highlighted fields.</strong>
        @foreach($errors->all() as $error)<p>{{ $error }}</p>@endforeach
    </div>
@endif
