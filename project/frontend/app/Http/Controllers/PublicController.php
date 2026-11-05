<?php

namespace App\Http\Controllers;

use App\Contracts\SkillSyncGateway;
use Illuminate\Database\Eloquent\ModelNotFoundException;
use Illuminate\Http\Response;
use Illuminate\View\View;
use Symfony\Component\HttpKernel\Exception\HttpExceptionInterface;

class PublicController extends Controller
{
    public function home(SkillSyncGateway $gateway): View
    {
        try {
            $categories = $gateway->categories()['data'];
            $workers = $gateway->workers(['available' => true], 1, 3)['data'];
            $preview = $workers[0] ?? null;

            return view('public.home', compact('categories', 'workers', 'preview'));
        } catch (\Throwable $exception) {
            report($exception);

            return view('public.home', ['categories' => [], 'workers' => [], 'serviceError' => 'The service directory is temporarily unavailable. Please try again shortly.']);
        }
    }

    public function services(SkillSyncGateway $gateway): View
    {
        try {
            return view('public.services', ['categories' => $gateway->categories()['data']]);
        } catch (\Throwable $exception) {
            report($exception);

            return view('public.services', ['categories' => [], 'serviceError' => 'Service categories are unavailable right now. Please try again.']);
        }
    }

    public function worker(string $workerId, SkillSyncGateway $gateway): View|Response
    {
        try {
            $worker = $gateway->worker($workerId)['data'];
        } catch (\Throwable $exception) {
            if ($exception instanceof ModelNotFoundException || ($exception instanceof HttpExceptionInterface && $exception->getStatusCode() === 404)) {
                return response()->view('public.not-found', [], 404);
            }
            report($exception);

            return response()->view('public.unavailable', [], 503);
        }
        abort_unless($worker, 404);

        return view('public.worker', compact('worker'));
    }

    public function about(): View
    {
        return view('public.about');
    }
}
