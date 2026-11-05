@if($operationErrors || $serviceError)
    <div class="ss-alert ss-alert-error" role="alert">
        <div>
            @foreach($operationErrors as $message)
                <p>{{ $message }}</p>
            @endforeach
            @if($serviceError)<p>{{ $serviceError }}</p>@endif
        </div>
    </div>
@endif
