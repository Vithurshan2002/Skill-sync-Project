<?php

namespace App\Http\Controllers;

use App\Services\SkillSync\BackendClient;
use App\Services\SkillSync\BackendIdentity;
use Illuminate\Auth\AuthenticationException;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Validation\Rule;
use Illuminate\View\View;
use Symfony\Component\HttpKernel\Exception\HttpException;

class AuthController extends Controller
{
    public function __invoke(Request $request, BackendClient $api): RedirectResponse
    {
        return $this->logout($request, $api);
    }

    public function loginPage(): View
    {
        return view('public.login');
    }

    public function registerPage(): View
    {
        return view('public.register');
    }

    public function login(Request $request, BackendClient $api, BackendIdentity $identity): RedirectResponse
    {
        $request->merge(['email' => strtolower(trim((string) $request->input('email')))]);
        $input = $request->validate(['email' => ['required', 'email'], 'password' => ['required', 'string', 'max:128']]);
        try {
            $result = $api->send('POST', '/auth/login', $input, false);
        } catch (HttpException $exception) {
            if ($exception->getStatusCode() !== 503) {
                throw $exception;
            }

            return back()->withErrors(['email' => 'Sign in is temporarily unavailable. Please try again.'])->withInput($request->only('email'));
        }
        $user = $identity->signIn($result['data']);
        $intended = $request->session()->pull('url.intended');
        $path = $intended ? parse_url($intended, PHP_URL_PATH) : null;
        if (is_string($path) && str_starts_with($path, '/'.$user->role.'/')) {
            return redirect()->to($path.(parse_url($intended, PHP_URL_QUERY) ? '?'.parse_url($intended, PHP_URL_QUERY) : ''));
        }

        return redirect('/'.$user->role.'/dashboard');
    }

    public function register(Request $request, BackendClient $api, BackendIdentity $identity): RedirectResponse
    {
        $request->merge(['email' => strtolower(trim((string) $request->input('email')))]);
        $input = $request->validate([
            'name' => ['required', 'string', 'min:2', 'max:100'],
            'email' => ['required', 'email', 'max:254'],
            'role' => ['required', Rule::in(['customer', 'worker'])],
            'town' => ['required', 'string', 'min:2', 'max:100'],
            'password' => ['required', 'string', 'min:8', 'max:128'],
            'password_confirmation' => ['bail', 'required', 'string', 'max:128', 'same:password'],
        ], [
            'password_confirmation.required' => 'Please confirm your password.',
            'password_confirmation.same' => 'The passwords do not match.',
        ]);
        unset($input['password_confirmation']);
        try {
            $result = $api->send('POST', '/auth/register', $input, false);
        } catch (HttpException $exception) {
            if ($exception->getStatusCode() !== 503) {
                throw $exception;
            }

            return back()->withErrors(['email' => 'Registration could not be confirmed. Try signing in before submitting again.'])->withInput($request->only('name', 'email', 'role', 'town'));
        }
        $user = $identity->signIn($result['data']);

        return redirect('/'.$user->role.($user->role === 'worker' ? '/profile' : '/dashboard'))
            ->with('status', $user->role === 'worker' ? 'Complete your profile to become available for jobs.' : 'Your account is ready.');
    }

    public function logout(Request $request, BackendClient $api): RedirectResponse
    {
        $message = 'You are signed out.';
        try {
            $api->send('POST', '/auth/logout');
        } catch (AuthenticationException) {
            // Expired tokens are already unusable.
        } catch (HttpException) {
            $message = 'You are signed out on this device. The service could not confirm token revocation.';
        } finally {
            Auth::logout();
            $request->session()->invalidate();
            $request->session()->regenerateToken();
        }

        return redirect('/')->with('status', $message);
    }
}
