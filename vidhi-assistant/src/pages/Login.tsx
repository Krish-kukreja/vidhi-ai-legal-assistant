import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Shield, Phone, CreditCard, User } from "lucide-react";
import { toast } from "@/hooks/use-toast";
import { saveUserData } from "@/utils/userStorage";
import type { UserData } from "@/utils/userStorage";

const Login = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);

  // Aadhaar login
  const [aadhaarNumber, setAadhaarNumber] = useState("");
  const [aadhaarName, setAadhaarName] = useState("");
  const [aadhaarOtp, setAadhaarOtp] = useState("");
  const [aadhaarOtpSent, setAadhaarOtpSent] = useState(false);

  // Phone login
  const [phoneNumber, setPhoneNumber] = useState("");
  const [phoneName, setPhoneName] = useState("");
  const [phoneOtp, setPhoneOtp] = useState("");
  const [phoneOtpSent, setPhoneOtpSent] = useState(false);

  // Guest mode
  const handleGuestLogin = () => {
    const userData: UserData = {
      name: "Guest User",
      authMethod: "guest",
      joinedDate: new Date().toLocaleDateString("en-IN", {
        day: "numeric",
        month: "long",
        year: "numeric",
      }),
      totalChats: 0,
      lastActive: "Just now",
    };
    saveUserData(userData);
    localStorage.setItem("vidhi_auth", "guest");

    toast({
      title: "Guest Mode",
      description: "You can use VIDHI without authentication. Some features may be limited.",
    });
    navigate("/");
  };

  // Aadhaar authentication
  const [expectedAadhaarOtp, setExpectedAadhaarOtp] = useState("");

  const handleAadhaarSendOtp = async () => {
    if (aadhaarNumber.length !== 12) {
      toast({
        title: "Invalid Aadhaar",
        description: "Please enter a valid 12-digit Aadhaar number",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    // Generate a random 6-digit OTP
    const generatedOtp = Math.floor(100000 + Math.random() * 900000).toString();
    setExpectedAadhaarOtp(generatedOtp);

    // Simulate OTP sending
    setTimeout(() => {
      setAadhaarOtpSent(true);
      setIsLoading(false);
      toast({
        title: "OTP Sent Successfully",
        description: `Your VIDHI OTP is: ${generatedOtp}`,
        duration: 8000,
      });
    }, 1500);
  };

  const handleAadhaarVerify = async () => {
    if (aadhaarOtp !== expectedAadhaarOtp) {
      toast({
        title: "Invalid OTP",
        description: "The OTP you entered is incorrect. Please try again.",
        variant: "destructive",
      });
      return;
    }

    if (!aadhaarName.trim()) {
      toast({
        title: "Name Required",
        description: "Please enter your name",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    // Simulate OTP verification delay
    setTimeout(() => {
      setIsLoading(false);

      // Save user data
      const userData: UserData = {
        name: aadhaarName.trim(),
        authMethod: "aadhaar",
        identifier: aadhaarNumber,
        joinedDate: new Date().toLocaleDateString("en-IN", {
          day: "numeric",
          month: "long",
          year: "numeric",
        }),
        totalChats: 0,
        lastActive: "Just now",
      };
      saveUserData(userData);
      localStorage.setItem("vidhi_auth", "aadhaar_" + aadhaarNumber);

      toast({
        title: "Authentication Successful",
        description: `Welcome to VIDHI, ${aadhaarName}!`,
      });
      navigate("/");
    }, 1000);
  };

  // Phone authentication
  const [expectedPhoneOtp, setExpectedPhoneOtp] = useState("");

  const handlePhoneSendOtp = async () => {
    if (phoneNumber.length !== 10) {
      toast({
        title: "Invalid Phone Number",
        description: "Please enter a valid 10-digit phone number",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    const generatedOtp = Math.floor(100000 + Math.random() * 900000).toString();
    setExpectedPhoneOtp(generatedOtp);

    setTimeout(() => {
      setPhoneOtpSent(true);
      setIsLoading(false);
      toast({
        title: "OTP Sent Successfully",
        description: `Your VIDHI OTP is: ${generatedOtp}`,
        duration: 8000,
      });
    }, 1500);
  };

  const handlePhoneVerify = async () => {
    if (phoneOtp !== expectedPhoneOtp) {
      toast({
        title: "Invalid OTP",
        description: "The OTP you entered is incorrect. Please try again.",
        variant: "destructive",
      });
      return;
    }

    if (!phoneName.trim()) {
      toast({
        title: "Name Required",
        description: "Please enter your name",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);

      // Save user data
      const userData: UserData = {
        name: phoneName.trim(),
        authMethod: "phone",
        identifier: phoneNumber,
        joinedDate: new Date().toLocaleDateString("en-IN", {
          day: "numeric",
          month: "long",
          year: "numeric",
        }),
        totalChats: 0,
        lastActive: "Just now",
      };
      saveUserData(userData);
      localStorage.setItem("vidhi_auth", "phone_" + phoneNumber);

      toast({
        title: "Authentication Successful",
        description: `Welcome to VIDHI, ${phoneName}!`,
      });
      navigate("/");
    }, 1000);
  };

  // Digilocker integration (mock)
  const handleDigilockerLogin = () => {
    toast({
      title: "Digilocker Integration",
      description: "Redirecting to Digilocker... (Feature coming soon)",
    });
    // In production, redirect to Digilocker OAuth
    // window.location.href = 'https://digilocker.gov.in/oauth/authorize?...'
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary/10 via-background to-accent/10 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <Shield className="h-16 w-16 text-primary" />
          </div>
          <CardTitle className="text-3xl font-bold">VIDHI</CardTitle>
          <CardDescription>
            Voice-Integrated Defense for Holistic Inclusion
          </CardDescription>
        </CardHeader>

        <CardContent>
          <Tabs defaultValue="guest" className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="guest">Guest</TabsTrigger>
              <TabsTrigger value="aadhaar">Aadhaar</TabsTrigger>
              <TabsTrigger value="phone">Phone</TabsTrigger>
            </TabsList>

            {/* Guest Mode */}
            <TabsContent value="guest" className="space-y-4">
              <div className="text-center space-y-4 py-6">
                <User className="h-12 w-12 mx-auto text-muted-foreground" />
                <div>
                  <h3 className="font-semibold text-lg">Continue as Guest</h3>
                  <p className="text-sm text-muted-foreground mt-2">
                    Access VIDHI without authentication. Some features like personalized scheme recommendations and chat history will be limited.
                  </p>
                </div>
                <Button onClick={handleGuestLogin} className="w-full" size="lg">
                  Continue as Guest
                </Button>
              </div>
            </TabsContent>

            {/* Aadhaar Authentication */}
            <TabsContent value="aadhaar" className="space-y-4">
              <div className="space-y-4 py-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <CreditCard className="h-4 w-4" />
                  <span>Secure Aadhaar-based authentication</span>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="aadhaar">Aadhaar Number</Label>
                  <Input
                    id="aadhaar"
                    type="text"
                    placeholder="Enter 12-digit Aadhaar number"
                    maxLength={12}
                    value={aadhaarNumber}
                    onChange={(e) => setAadhaarNumber(e.target.value.replace(/\D/g, ""))}
                    disabled={aadhaarOtpSent}
                  />
                </div>

                {aadhaarOtpSent && (
                  <>
                    <div className="space-y-2">
                      <Label htmlFor="aadhaar-name">Full Name</Label>
                      <Input
                        id="aadhaar-name"
                        type="text"
                        placeholder="Enter your full name"
                        value={aadhaarName}
                        onChange={(e) => setAadhaarName(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="aadhaar-otp">OTP</Label>
                      <Input
                        id="aadhaar-otp"
                        type="text"
                        placeholder="Enter 6-digit OTP"
                        maxLength={6}
                        value={aadhaarOtp}
                        onChange={(e) => setAadhaarOtp(e.target.value.replace(/\D/g, ""))}
                      />
                    </div>
                  </>
                )}

                {!aadhaarOtpSent ? (
                  <Button
                    onClick={handleAadhaarSendOtp}
                    disabled={isLoading || aadhaarNumber.length !== 12}
                    className="w-full"
                  >
                    {isLoading ? "Sending OTP..." : "Send OTP"}
                  </Button>
                ) : (
                  <div className="space-y-2">
                    <Button
                      onClick={handleAadhaarVerify}
                      disabled={isLoading || aadhaarOtp.length !== 6 || !aadhaarName.trim()}
                      className="w-full"
                    >
                      {isLoading ? "Verifying..." : "Verify & Login"}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => {
                        setAadhaarOtpSent(false);
                        setAadhaarOtp("");
                        setAadhaarName("");
                      }}
                      className="w-full"
                    >
                      Resend OTP
                    </Button>
                  </div>
                )}

                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-background px-2 text-muted-foreground">Or</span>
                  </div>
                </div>

                <Button
                  variant="outline"
                  onClick={handleDigilockerLogin}
                  className="w-full"
                >
                  <CreditCard className="mr-2 h-4 w-4" />
                  Login with Digilocker
                </Button>
              </div>
            </TabsContent>

            {/* Phone Authentication */}
            <TabsContent value="phone" className="space-y-4">
              <div className="space-y-4 py-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Phone className="h-4 w-4" />
                  <span>Login with your phone number</span>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="phone">Phone Number</Label>
                  <Input
                    id="phone"
                    type="tel"
                    placeholder="Enter 10-digit phone number"
                    maxLength={10}
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value.replace(/\D/g, ""))}
                    disabled={phoneOtpSent}
                  />
                </div>

                {phoneOtpSent && (
                  <>
                    <div className="space-y-2">
                      <Label htmlFor="phone-name">Full Name</Label>
                      <Input
                        id="phone-name"
                        type="text"
                        placeholder="Enter your full name"
                        value={phoneName}
                        onChange={(e) => setPhoneName(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="phone-otp">OTP</Label>
                      <Input
                        id="phone-otp"
                        type="text"
                        placeholder="Enter 6-digit OTP"
                        maxLength={6}
                        value={phoneOtp}
                        onChange={(e) => setPhoneOtp(e.target.value.replace(/\D/g, ""))}
                      />
                    </div>
                  </>
                )}

                {!phoneOtpSent ? (
                  <Button
                    onClick={handlePhoneSendOtp}
                    disabled={isLoading || phoneNumber.length !== 10}
                    className="w-full"
                  >
                    {isLoading ? "Sending OTP..." : "Send OTP"}
                  </Button>
                ) : (
                  <div className="space-y-2">
                    <Button
                      onClick={handlePhoneVerify}
                      disabled={isLoading || phoneOtp.length !== 6 || !phoneName.trim()}
                      className="w-full"
                    >
                      {isLoading ? "Verifying..." : "Verify & Login"}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => {
                        setPhoneOtpSent(false);
                        setPhoneOtp("");
                        setPhoneName("");
                      }}
                      className="w-full"
                    >
                      Resend OTP
                    </Button>
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>

          <div className="mt-6 text-center text-xs text-muted-foreground">
            <p>By continuing, you agree to VIDHI's Terms of Service and Privacy Policy</p>
            <p className="mt-2">🔒 Your data is encrypted and secure</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Login;
